"""Safe Windows-tool integrations for SyncScope's guided Tool Lab."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from typing import Any


REGISTRY_KEY = r"HKCU\Software\SyncScopeLab"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _require_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Windows Tool Lab is available only on Windows")


def _run(command: list[str], timeout: int = 12) -> subprocess.CompletedProcess[str]:
    _require_windows()
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "Windows tool returned an error").strip()
        raise RuntimeError(detail) from exc


def tool_status() -> list[dict[str, Any]]:
    """Report the three tool groups used by the lab."""
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    reg = shutil.which("reg.exe") or shutil.which("reg")
    regedit = shutil.which("regedit.exe") or shutil.which("regedit")
    return [
        {
            "id": "powershell",
            "name": "PowerShell",
            "available": bool(powershell),
            "path": powershell or "Not found",
            "purpose": "Process and thread inspection",
        },
        {
            "id": "wmi",
            "name": "WMI / CIM",
            "available": bool(powershell),
            "path": "root\\cimv2 via PowerShell" if powershell else "Not available",
            "purpose": "Win32_Process management data",
        },
        {
            "id": "registry",
            "name": "Registry toolchain",
            "available": bool(reg and regedit),
            "path": f"{reg or 'reg.exe missing'} · {regedit or 'regedit.exe missing'}",
            "purpose": "Safe HKCU configuration experiment",
        },
    ]


def powershell_process_snapshot(pid: int) -> dict[str, Any]:
    """Inspect one process with the Get-Process cmdlet."""
    command_text = (
        f"Get-Process -Id {int(pid)} | "
        "Select-Object Id,ProcessName,StartTime,Threads,Handles,WorkingSet64,VirtualMemorySize64 | "
        "ConvertTo-Json -Depth 3 -Compress"
    )
    completed = _run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command_text]
    )
    data = json.loads(completed.stdout.strip())
    threads = data.pop("Threads", []) or []
    data["ThreadCount"] = len(threads)
    return {
        "tool": "PowerShell",
        "command": f"Get-Process -Id {int(pid)}",
        "target_pid": int(pid),
        "data": data,
    }


def wmi_process_snapshot(pid: int) -> dict[str, Any]:
    """Query Win32_Process through the modern CIM cmdlets."""
    command_text = (
        f"Get-CimInstance Win32_Process -Filter \"ProcessId = {int(pid)}\" | "
        "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,ThreadCount,HandleCount,"
        "WorkingSetSize,VirtualSize,CreationDate,CommandLine | ConvertTo-Json -Compress"
    )
    completed = _run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command_text]
    )
    if not completed.stdout.strip():
        raise RuntimeError(f"WMI did not return process {pid}")
    return {
        "tool": "WMI / CIM",
        "namespace": r"root\cimv2",
        "class": "Win32_Process",
        "command": f'Get-CimInstance Win32_Process -Filter "ProcessId = {int(pid)}"',
        "target_pid": int(pid),
        "data": json.loads(completed.stdout.strip()),
    }


def registry_demo(pid: int) -> dict[str, Any]:
    """Create and query a project-owned HKCU key using reg.exe."""
    values = {
        "Project": ("REG_SZ", "SyncScope"),
        "TargetPID": ("REG_DWORD", str(int(pid))),
        "LastExperiment": ("REG_SZ", "Windows Tool Lab"),
    }
    commands: list[str] = []
    for name, (value_type, value) in values.items():
        command = ["reg.exe", "add", REGISTRY_KEY, "/v", name, "/t", value_type, "/d", value, "/f"]
        _run(command)
        commands.append(" ".join(command))
    query = _run(["reg.exe", "query", REGISTRY_KEY])
    return {
        "tool": "reg.exe",
        "registry_key": REGISTRY_KEY,
        "commands": commands,
        "query_command": f'reg query "{REGISTRY_KEY}"',
        "output": query.stdout.strip(),
        "values": {name: value for name, (_kind, value) in values.items()},
    }


def launch_regedit() -> dict[str, str]:
    """Open Registry Editor for manual inspection of the lab key."""
    _require_windows()
    executable = shutil.which("regedit.exe") or shutil.which("regedit")
    if not executable:
        raise RuntimeError("Registry Editor is not installed")
    try:
        os.startfile(executable, "runas")
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1223:
            raise RuntimeError("Registry Editor was not opened because the Windows permission prompt was cancelled.") from exc
        raise
    return {
        "tool": "Registry Editor",
        "status": "launched",
        "instruction": f"Paste {REGISTRY_KEY} into the Registry Editor address bar.",
    }
