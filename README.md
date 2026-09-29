# SyncScope

**A real-time interprocess communication and concurrency analysis platform.**

SyncScope turns operating-system concepts into experiments you can see and measure. It launches real child processes and compares pipes, message queues, shared memory, and sockets from a polished browser dashboard.

## Highlights

- Run real IPC transfers and watch the producer–consumer topology react.
- Measure latency, throughput, message rate, transferred bytes, and worker PIDs.
- Trigger an actual race condition with multiple processes sharing one counter.
- Enable a lock and compare the corrected result.
- Benchmark all IPC techniques with the same workload.
- Inspect SyncScope with real PowerShell and WMI/CIM queries.
- Create and verify a safe project Registry key using `reg.exe` and Regedit.
- Learn the trade-offs through a compact IPC reference and decision matrix.
- Works without third-party packages: only Python 3.10+ and a modern browser are required.

## Run on Windows

Double-click `run.bat`.

Or start it from a terminal:

```powershell
python app.py --open
```

SyncScope opens at [http://127.0.0.1:8765](http://127.0.0.1:8765). Press `Ctrl+C` in the terminal to stop it.

## Run on Linux or macOS

```bash
python3 app.py
```

Then open `http://127.0.0.1:8765`.

## Demo flow

1. Open **Live Lab**, select an IPC method, and run a transfer.
2. Compare worker PIDs, throughput, latency, and the execution timeline.
3. Open **Race Lab** and run the counter without synchronization.
4. Note the lost updates, enable the lock, and run it again.
5. Open **Benchmarks** and compare all four mechanisms.
6. Open **Tool Lab**, run the PowerShell and WMI inspections, and compare their results.
7. Create the Registry experiment, open Regedit, and inspect `HKCU\Software\SyncScopeLab`.
8. Use **Learn** to explain why the results and design trade-offs differ.

## Architecture

```text
Browser dashboard
       │ HTTP + job polling
       ▼
Python local server
       │
       ├── Pipe worker process
       ├── Queue worker process
       ├── Shared-memory worker + semaphores
       ├── Socket worker process
       ├── Shared-counter workers + optional lock
       └── Windows Tool Lab
           ├── PowerShell Get-Process
           ├── WMI/CIM Win32_Process
           └── reg.exe + Registry Editor
```

The interface is implemented with semantic HTML, responsive CSS, and vanilla JavaScript. The server and experiment engine use only the Python standard library. Background jobs keep the dashboard responsive while operating-system processes execute the experiments.

## Windows Tool Lab

The Tool Lab targets the running SyncScope server PID so every result is live and easy to verify during a presentation. PowerShell reports process-level statistics, WMI exposes the same process through `Win32_Process`, and `reg.exe` creates a non-administrative demonstration key under the current user's Registry hive. The Regedit button opens Registry Editor so the generated values can be inspected visually.

## Test

From the project folder:

```powershell
python -m unittest discover -s tests -v
```

## Safety

SyncScope binds to `127.0.0.1` by default, validates experiment limits, and does not require administrator access. The experiments create short-lived local processes only.

## Project title

**Design and Development of SyncScope: A Real-Time Interprocess Communication and Concurrency Analysis Platform**

## License

MIT
