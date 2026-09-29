"""Real interprocess communication experiments used by SyncScope.

The functions in this module are intentionally top-level so they are safe to
spawn on Windows, where multiprocessing starts a fresh Python interpreter.
"""

from __future__ import annotations

import multiprocessing as mp
from multiprocessing import shared_memory
import os
import queue
import socket
import time
from typing import Any, Callable


def _pipe_reader(connection, count: int, ready, pid_queue) -> None:
    pid_queue.put(os.getpid())
    ready.set()
    for _ in range(count):
        connection.recv_bytes()
    connection.close()


def _queue_reader(message_queue, count: int, ready, pid_queue) -> None:
    pid_queue.put(os.getpid())
    ready.set()
    for _ in range(count):
        message_queue.get()


def _shared_memory_reader(
    memory_name: str,
    count: int,
    data_ready,
    consumed,
    ready,
    pid_queue,
) -> None:
    memory = shared_memory.SharedMemory(name=memory_name)
    pid_queue.put(os.getpid())
    ready.set()
    checksum = 0
    try:
        for _ in range(count):
            data_ready.acquire()
            checksum ^= memory.buf[0]
            consumed.release()
    finally:
        memory.close()
    # Keep the read observable to the interpreter.
    if checksum < 0:  # pragma: no cover
        raise RuntimeError("unreachable")


def _socket_reader(sock, count: int, payload_size: int, ready, pid_queue) -> None:
    pid_queue.put(os.getpid())
    ready.set()
    remaining = count * payload_size
    while remaining:
        data = sock.recv(min(65_536, remaining))
        if not data:
            break
        remaining -= len(data)
    sock.close()


def _race_worker(counter, iterations: int, lock, synchronized: bool, race_barrier, pid_queue) -> None:
    pid_queue.put(os.getpid())
    for index in range(iterations):
        if synchronized:
            with lock:
                counter.value += 1
        else:
            current = counter.value
            # Periodically align the workers between their read and write. This
            # makes the lost-update bug repeatable enough for a classroom demo
            # instead of leaving it entirely to the OS scheduler's timing.
            if index % 10 == 0:
                race_barrier.wait()
            counter.value = current + 1
            if index % 10 == 0:
                race_barrier.wait()


def _result(method: str, elapsed: float, messages: int, payload_size: int, pids: list[int]) -> dict[str, Any]:
    total_bytes = messages * payload_size
    safe_elapsed = max(elapsed, 1e-9)
    return {
        "method": method,
        "elapsed_ms": round(safe_elapsed * 1000, 3),
        "latency_ms": round((safe_elapsed / messages) * 1000, 4),
        "throughput_mbps": round((total_bytes * 8 / safe_elapsed) / 1_000_000, 3),
        "messages_per_second": round(messages / safe_elapsed),
        "bytes_transferred": total_bytes,
        "worker_pids": pids,
    }


def benchmark_pipe(messages: int, payload_size: int) -> dict[str, Any]:
    receive_connection, send_connection = mp.Pipe(duplex=False)
    ready = mp.Event()
    pid_queue = mp.Queue()
    process = mp.Process(target=_pipe_reader, args=(receive_connection, messages, ready, pid_queue))
    process.start()
    receive_connection.close()
    ready.wait(5)
    payload = b"P" * payload_size
    started = time.perf_counter()
    for _ in range(messages):
        send_connection.send_bytes(payload)
    send_connection.close()
    process.join(15)
    elapsed = time.perf_counter() - started
    if process.is_alive():
        process.terminate()
        process.join()
        raise TimeoutError("Pipe worker did not finish")
    return _result("pipe", elapsed, messages, payload_size, [pid_queue.get(timeout=1)])


def benchmark_queue(messages: int, payload_size: int) -> dict[str, Any]:
    message_queue = mp.Queue(maxsize=min(messages, 256))
    ready = mp.Event()
    pid_queue = mp.Queue()
    process = mp.Process(target=_queue_reader, args=(message_queue, messages, ready, pid_queue))
    process.start()
    ready.wait(5)
    payload = b"Q" * payload_size
    started = time.perf_counter()
    for _ in range(messages):
        message_queue.put(payload)
    process.join(15)
    elapsed = time.perf_counter() - started
    if process.is_alive():
        process.terminate()
        process.join()
        raise TimeoutError("Queue worker did not finish")
    result = _result("queue", elapsed, messages, payload_size, [pid_queue.get(timeout=1)])
    message_queue.close()
    return result


def benchmark_shared_memory(messages: int, payload_size: int) -> dict[str, Any]:
    memory = shared_memory.SharedMemory(create=True, size=payload_size)
    data_ready = mp.Semaphore(0)
    consumed = mp.Semaphore(0)
    ready = mp.Event()
    pid_queue = mp.Queue()
    process = mp.Process(
        target=_shared_memory_reader,
        args=(memory.name, messages, data_ready, consumed, ready, pid_queue),
    )
    process.start()
    ready.wait(5)
    payload = b"S" * payload_size
    started = time.perf_counter()
    try:
        for _ in range(messages):
            memory.buf[:payload_size] = payload
            data_ready.release()
            consumed.acquire()
        process.join(15)
        elapsed = time.perf_counter() - started
        if process.is_alive():
            process.terminate()
            process.join()
            raise TimeoutError("Shared-memory worker did not finish")
        return _result("shared_memory", elapsed, messages, payload_size, [pid_queue.get(timeout=1)])
    finally:
        memory.close()
        memory.unlink()


def benchmark_socket(messages: int, payload_size: int) -> dict[str, Any]:
    parent_socket, child_socket = socket.socketpair()
    ready = mp.Event()
    pid_queue = mp.Queue()
    process = mp.Process(target=_socket_reader, args=(child_socket, messages, payload_size, ready, pid_queue))
    process.start()
    child_socket.close()
    ready.wait(5)
    payload = b"N" * payload_size
    started = time.perf_counter()
    for _ in range(messages):
        parent_socket.sendall(payload)
    parent_socket.shutdown(socket.SHUT_WR)
    parent_socket.close()
    process.join(15)
    elapsed = time.perf_counter() - started
    if process.is_alive():
        process.terminate()
        process.join()
        raise TimeoutError("Socket worker did not finish")
    return _result("socket", elapsed, messages, payload_size, [pid_queue.get(timeout=1)])


BENCHMARKS: dict[str, Callable[[int, int], dict[str, Any]]] = {
    "pipe": benchmark_pipe,
    "queue": benchmark_queue,
    "shared_memory": benchmark_shared_memory,
    "socket": benchmark_socket,
}


def run_benchmark(method: str, messages: int, payload_size: int) -> dict[str, Any]:
    if method not in BENCHMARKS:
        raise ValueError(f"Unsupported IPC method: {method}")
    return BENCHMARKS[method](messages, payload_size)


def run_race(workers: int, iterations: int, synchronized: bool) -> dict[str, Any]:
    counter = mp.Value("i", 0, lock=False)
    lock = mp.Lock()
    race_barrier = mp.Barrier(workers)
    pid_queue = mp.Queue()
    processes = [
        mp.Process(target=_race_worker, args=(counter, iterations, lock, synchronized, race_barrier, pid_queue))
        for _ in range(workers)
    ]
    started = time.perf_counter()
    for process in processes:
        process.start()
    for process in processes:
        process.join(15)
    elapsed = time.perf_counter() - started
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join()
            raise TimeoutError("Race-condition worker did not finish")
    pids: list[int] = []
    while True:
        try:
            pids.append(pid_queue.get_nowait())
        except queue.Empty:
            break
    expected = workers * iterations
    actual = counter.value
    return {
        "synchronized": synchronized,
        "workers": workers,
        "iterations": iterations,
        "expected": expected,
        "actual": actual,
        "lost_updates": expected - actual,
        "accuracy_percent": round((actual / expected) * 100, 2),
        "elapsed_ms": round(elapsed * 1000, 3),
        "worker_pids": sorted(pids),
    }


def compare_methods(messages: int, payload_size: int, progress: Callable[[str, dict[str, Any]], None] | None = None) -> list[dict[str, Any]]:
    results = []
    for method, benchmark in BENCHMARKS.items():
        if progress:
            progress(method, {"phase": "started"})
        result = benchmark(messages, payload_size)
        results.append(result)
        if progress:
            progress(method, {"phase": "completed", "result": result})
    return results
