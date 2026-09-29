# SyncScope Project Report

## Title

**Design and Development of SyncScope: A Real-Time Interprocess Communication and Concurrency Analysis Platform**

## Abstract

SyncScope is an interactive systems laboratory that demonstrates how independent operating-system processes exchange data and coordinate access to shared resources. The platform executes real child processes and presents their behavior through a responsive browser dashboard. It supports anonymous pipes, message queues, shared memory, and local sockets, and records transfer latency, throughput, message rate, data volume, and process identifiers. A separate concurrency laboratory intentionally creates a race condition on a shared counter and compares the result with a lock-protected execution. Its Windows Tool Lab uses PowerShell, WMI/CIM, `reg.exe`, and Registry Editor to inspect the running application and verify operating-system data with real utilities. SyncScope connects operating-system theory with observable evidence and gives students a repeatable way to analyze IPC, concurrency, process management, and Registry concepts.

## Problem statement

IPC and synchronization are usually taught with diagrams or small console programs. These approaches make it difficult to observe execution, compare mechanisms under the same workload, or see why synchronization is required. SyncScope provides one visual environment where students can run, measure, and compare real experiments.

## Objectives

- Demonstrate four common IPC mechanisms with real processes.
- Visualize producer–consumer communication and worker process identity.
- Measure latency, throughput, and messages per second.
- Reproduce the lost-update race condition reliably.
- Demonstrate how a mutual-exclusion lock protects a critical section.
- Provide an interactive comparison and learning reference.
- Run safely on a normal computer without administrator access.

## Modules

### 1. Live IPC laboratory

The user selects a communication mechanism, message count, and payload size. SyncScope creates a worker process, transfers data, and reports measured results. The interface displays the participating PIDs and an animated communication topology.

### 2. Race-condition laboratory

Multiple worker processes increment a shared integer. In unprotected mode, the read-modify-write sequence overlaps and updates are lost. In protected mode, a lock restricts the critical section to one worker at a time, producing the expected result.

### 3. Benchmark suite

Pipes, queues, shared memory, and sockets run with the same message count and payload size. Results are displayed in a throughput chart and comparison table.

### 4. IPC field guide

The learning view summarizes each mechanism's data model, synchronization needs, scope, advantages, and appropriate use cases.

### 5. Windows Tool Lab

The Tool Lab runs `Get-Process` in PowerShell against the SyncScope server PID, queries the same PID from the WMI `Win32_Process` class through `Get-CimInstance`, and presents both outputs for comparison. A Registry experiment uses `reg.exe` to create and query `HKCU\Software\SyncScopeLab`; Registry Editor can then be opened for visual verification. The key is limited to the current user and does not require administrator access.

## System architecture

```text
User
 │
 ▼
Responsive browser dashboard
 │  REST requests and job-status polling
 ▼
Threaded Python HTTP server
 │
 ├─ Experiment job manager
 ├─ Pipe producer/consumer
 ├─ Queue producer/consumer
 ├─ Shared-memory region + semaphores
 ├─ Socket pair
 ├─ Shared counter + optional mutex lock
 └─ Windows tool adapters
     ├─ PowerShell Get-Process
     ├─ WMI/CIM Win32_Process
     └─ reg.exe and Registry Editor
```

## Technology

- Python standard library
- Python `multiprocessing` and `shared_memory`
- Local sockets
- Semantic HTML5
- Responsive CSS
- Vanilla JavaScript
- Git and GitHub
- PowerShell and WMI/CIM
- Windows Registry tools (`reg.exe` and Regedit)

No third-party runtime dependencies are required.

## Key concepts demonstrated

- Process creation and process identifiers
- Data serialization and copying
- Shared addressable regions
- Producer–consumer communication
- Mutual exclusion and critical sections
- Race conditions and lost updates
- Semaphores and process coordination
- Latency and throughput
- Asynchronous experiment execution

## Testing

The automated test suite verifies that every IPC method transfers the expected number of bytes, the synchronized counter reaches the exact expected value, the unprotected counter exhibits lost updates, and invalid communication mechanisms are rejected. The complete browser-to-server flow was also tested with a live pipe experiment.

## Demonstration sequence

1. Start SyncScope with `run.bat`.
2. Run a pipe transfer and identify the producer and consumer PIDs.
3. Select shared memory and explain why explicit synchronization is present.
4. Open Race Lab and run the unprotected shared counter.
5. Compare the actual and expected results.
6. Enable the synchronization lock and repeat the experiment.
7. Run the four-method benchmark and discuss the measured differences.
8. Open the Learn view and summarize when each mechanism is appropriate.
9. Open Tool Lab and inspect the SyncScope PID with PowerShell.
10. Query the same PID through WMI and compare the fields.
11. Create the project Registry key with `reg.exe` and verify it in Regedit.

## Limitations

- Performance measurements include local scheduling and Python runtime overhead.
- Results vary with hardware, operating-system load, and message size.
- The toolkit models local processes and does not benchmark remote network hosts.
- The shared-memory benchmark prioritizes a clear synchronized demonstration rather than maximum theoretical bandwidth.

## Future enhancements

- Deadlock detection and resource-allocation visualization
- Thread scheduling and context-switch experiments
- Named-pipe support
- Experiment history export to CSV or PDF
- Remote client/server socket experiments
- Windows performance-counter integration

## Conclusion

SyncScope converts IPC and concurrency concepts into observable experiments. By combining real operating-system processes with live measurements and visual explanations, it provides a stronger learning and demonstration experience than isolated console programs.

## Viva questions

1. Why can two processes not normally access each other's memory directly?
2. How does shared memory differ from a pipe?
3. Why is shared memory fast, and why does it require synchronization?
4. What is a critical section?
5. How does a lock prevent lost updates?
6. What is the difference between concurrency and parallelism?
7. When would a socket be preferable to a message queue?
8. Why can benchmark results change between runs?
9. What is the difference between latency and throughput?
10. Why does SyncScope create child processes rather than only simulating them?
