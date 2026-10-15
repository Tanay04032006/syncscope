"""SyncScope local web server and experiment API (standard library only)."""

from __future__ import annotations

import argparse
import errno
from collections import OrderedDict
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import subprocess
import threading
import time
import traceback
import uuid
import webbrowser

from ipc_engine import compare_methods, run_benchmark, run_race
from windows_tools import (
    launch_regedit,
    powershell_process_snapshot,
    registry_demo,
    tool_status,
    wmi_process_snapshot,
)


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
MAX_BODY_BYTES = 64 * 1024


class JobStore:
    def __init__(self) -> None:
        self._jobs: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()

    def create(self, kind: str, settings: dict) -> str:
        job_id = uuid.uuid4().hex[:12]
        now = time.time()
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "kind": kind,
                "status": "queued",
                "settings": settings,
                "created_at": now,
                "updated_at": now,
                "events": [{"time": now, "level": "info", "message": "Experiment queued"}],
                "result": None,
                "error": None,
            }
            while len(self._jobs) > 50:
                self._jobs.popitem(last=False)
        return job_id

    def update(self, job_id: str, **changes) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.update(changes)
            job["updated_at"] = time.time()

    def event(self, job_id: str, message: str, level: str = "info", **data) -> None:
        with self._lock:
            self._jobs[job_id]["events"].append(
                {"time": time.time(), "level": level, "message": message, **data}
            )
            self._jobs[job_id]["updated_at"] = time.time()

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return json.loads(json.dumps(job)) if job else None

    def active_count(self) -> int:
        with self._lock:
            return sum(job["status"] in {"queued", "running"} for job in self._jobs.values())


JOBS = JobStore()


def _validated_int(value, minimum: int, maximum: int, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def _execute(job_id: str, kind: str, settings: dict) -> None:
    JOBS.update(job_id, status="running")
    JOBS.event(job_id, "Worker processes are starting", "active")
    try:
        if kind == "ipc":
            method = settings.get("method", "pipe")
            messages = _validated_int(settings.get("messages", 500), 10, 10_000, "messages")
            payload_size = _validated_int(settings.get("payload_size", 1024), 1, 1_048_576, "payload size")
            JOBS.event(job_id, f"Running {method.replace('_', ' ')} transfer", "active", method=method)
            result = run_benchmark(method, messages, payload_size)
            JOBS.event(job_id, f"Transferred {result['bytes_transferred']:,} bytes", "success")
        elif kind == "race":
            workers = _validated_int(settings.get("workers", 4), 2, 12, "workers")
            iterations = _validated_int(settings.get("iterations", 2500), 100, 50_000, "iterations")
            synchronized = bool(settings.get("synchronized", False))
            label = "protected" if synchronized else "unprotected"
            JOBS.event(job_id, f"Launching {workers} {label} counter workers", "active")
            result = run_race(workers, iterations, synchronized)
            JOBS.event(job_id, f"Observed {result['lost_updates']:,} lost updates", "success")
        elif kind == "benchmark":
            messages = _validated_int(settings.get("messages", 500), 10, 5_000, "messages")
            payload_size = _validated_int(settings.get("payload_size", 4096), 1, 262_144, "payload size")

            def progress(method: str, data: dict) -> None:
                if data["phase"] == "started":
                    JOBS.event(job_id, f"Benchmarking {method.replace('_', ' ')}", "active", method=method)
                else:
                    JOBS.event(job_id, f"{method.replace('_', ' ').title()} complete", "success", method=method)

            result = {"results": compare_methods(messages, payload_size, progress)}
        else:
            raise ValueError("Unknown experiment type")
        JOBS.update(job_id, status="completed", result=result)
        JOBS.event(job_id, "Experiment completed", "success")
    except Exception as exc:  # Keep the UI responsive and expose a useful error.
        JOBS.update(job_id, status="failed", error=str(exc))
        JOBS.event(job_id, f"Experiment failed: {exc}", "error")
        traceback.print_exc()


class SyncScopeHandler(SimpleHTTPRequestHandler):
    server_version = "SyncScope/1.0"

    def end_headers(self) -> None:
        # Reloads must pick up local code changes rather than stale JS or CSS.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def _json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY_BYTES:
            raise ValueError("Request is too large")
        raw = self.rfile.read(length)
        return json.loads(raw or b"{}")

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._json({"status": "ok", "name": "SyncScope", "version": "1.0.0"})
            return
        if self.path == "/api/system":
            self._json(
                {
                    "platform": platform.system(),
                    "release": platform.release(),
                    "architecture": platform.machine(),
                    "python": platform.python_version(),
                    "server_pid": os.getpid(),
                    "cpu_count": os.cpu_count(),
                    "active_jobs": JOBS.active_count(),
                }
            )
            return
        if self.path == "/api/tools/status":
            tools = tool_status()
            self._json(
                {
                    "tools": tools,
                    "available": sum(bool(tool["available"]) for tool in tools),
                    "total": len(tools),
                    "target_pid": os.getpid(),
                }
            )
            return
        if self.path.startswith("/api/jobs/"):
            job_id = self.path.rsplit("/", 1)[-1]
            job = JOBS.get(job_id)
            if job:
                self._json(job)
            else:
                self._json({"error": "Experiment not found"}, HTTPStatus.NOT_FOUND)
            return
        super().do_GET()

    def do_POST(self) -> None:
        tool_actions = {
            "/api/tools/powershell": lambda: powershell_process_snapshot(os.getpid()),
            "/api/tools/wmi": lambda: wmi_process_snapshot(os.getpid()),
            "/api/tools/registry": lambda: registry_demo(os.getpid()),
            "/api/tools/regedit": launch_regedit,
        }
        if self.path in tool_actions:
            try:
                self._json(tool_actions[self.path]())
            except (RuntimeError, subprocess.SubprocessError, OSError, json.JSONDecodeError) as exc:
                self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if self.path not in {"/api/experiments/ipc", "/api/experiments/race", "/api/experiments/benchmark"}:
            self._json({"error": "Route not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            settings = self._body()
            kind = self.path.rsplit("/", 1)[-1]
            job_id = JOBS.create(kind, settings)
            thread = threading.Thread(target=_execute, args=(job_id, kind, settings), daemon=True)
            thread.start()
            self._json({"job_id": job_id, "status": "queued"}, HTTPStatus.ACCEPTED)
        except (ValueError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def run(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False, auto_port: bool = False) -> None:
    mp.freeze_support()
    for candidate in range(port, min(port + (20 if auto_port else 1), 65536)):
        try:
            server = ThreadingHTTPServer((host, candidate), SyncScopeHandler)
            break
        except OSError as exc:
            if not auto_port or (exc.errno != errno.EADDRINUSE and getattr(exc, "winerror", None) not in {10048, 10013}):
                raise
    else:
        raise RuntimeError("No available port found. Close an old SyncScope terminal or choose another --port.")
    if candidate != port:
        print(f"Port {port} is busy. Using port {candidate}; no existing application was stopped.")
    port = server.server_address[1]
    print(f"SyncScope is running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.7, lambda: webbrowser.open(f"http://{host}:{port}/?v=ipc-scenes-3")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SyncScope...")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the SyncScope IPC laboratory")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="Open SyncScope in the default browser")
    parser.add_argument("--no-open", action="store_false", dest="open", help="Do not open a browser")
    parser.add_argument("--auto-port", action="store_true", help="Try nearby ports when the requested port is busy")
    arguments = parser.parse_args()
    if not 1 <= arguments.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    run(arguments.host, arguments.port, arguments.open, arguments.auto_port)
