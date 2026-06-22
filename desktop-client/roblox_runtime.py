"""Roblox runtime provenance: memory regions, module trust, drivers, launch chain, handle proxy."""
from __future__ import annotations

import json
import platform
import re
import subprocess
from datetime import datetime, timezone
from typing import Any, Callable

import psutil

ROBLOX_PROCESS_NAMES = frozenset({"robloxplayerbeta.exe", "robloxplayer.exe", "roblox.exe"})
ROBLOX_TRUSTED_LAUNCHER_NAMES = frozenset(
    {
        "explorer.exe",
        "bloxstrap.exe",
        "fishstrap.exe",
        "robloxplayerbeta.exe",
        "robloxplayerlauncher.exe",
        "roblox.exe",
    }
)
ROBLOX_TRUSTED_LAUNCHER_FRAGMENTS = (
    "\\roblox\\versions\\",
    "\\bloxstrap\\",
    "\\fishstrap\\",
    "robloxplayerbeta.exe",
    "robloxplayerlauncher.exe",
)
ROBLOX_MODULE_TRUSTED_FRAGMENTS = (
    "\\windows\\",
    "\\program files\\",
    "\\program files (x86)\\",
    "\\roblox\\",
    "\\nvidia\\",
    "\\amd\\",
    "\\intel\\",
    "\\microsoft\\",
)
SUSPICIOUS_DRIVER_KEYWORDS = (
    "kdmapper",
    "capcom",
    "gdrv",
    "asio",
    "cheat",
    "hack",
    "inject",
    "vulnerable",
    "dbk",
    "rtcore",
)


def _run_command(command: list[str], *, timeout: float = 12.0, max_chars: int = 16000) -> str:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        return output[:max_chars]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Unavailable: {exc}"


def _find_roblox_processes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for proc in psutil.process_iter(["pid", "name", "exe", "create_time", "ppid"]):
        try:
            info = proc.info
            name = str(info.get("name") or "").lower()
            if name not in ROBLOX_PROCESS_NAMES:
                continue
            rows.append(
                {
                    "pid": int(info["pid"]),
                    "name": info.get("name"),
                    "exe": info.get("exe"),
                    "ppid": info.get("ppid"),
                    "create_time": info.get("create_time"),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, ValueError):
            continue
    return rows


def _resolve_process_brief(pid: int | None) -> dict[str, Any]:
    if not pid:
        return {}
    try:
        proc = psutil.Process(int(pid))
        info = proc.as_dict(attrs=["pid", "name", "exe", "cmdline", "create_time"])
        return {
            "pid": info.get("pid"),
            "name": info.get("name"),
            "exe": info.get("exe"),
            "cmdline": " ".join(info.get("cmdline") or [])[:420],
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {"pid": pid}


def _scan_launch_provenance(roblox_rows: list[dict[str, Any]]) -> dict[str, Any]:
    anomalies: list[dict[str, Any]] = []
    chains: list[dict[str, Any]] = []
    for row in roblox_rows:
        chain: list[dict[str, Any]] = []
        current_pid = row.get("pid")
        seen: set[int] = set()
        for _ in range(6):
            if not current_pid or current_pid in seen:
                break
            seen.add(int(current_pid))
            brief = _resolve_process_brief(int(current_pid))
            if not brief:
                break
            chain.append(brief)
            try:
                current_pid = psutil.Process(int(current_pid)).ppid()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
        chains.append({"roblox_pid": row.get("pid"), "chain": chain})
        if len(chain) < 2:
            continue
        parent = chain[1]
        parent_name = str(parent.get("name") or "").lower()
        parent_exe = str(parent.get("exe") or "").lower()
        trusted = parent_name in ROBLOX_TRUSTED_LAUNCHER_NAMES or any(
            frag in parent_exe for frag in ROBLOX_TRUSTED_LAUNCHER_FRAGMENTS
        )
        if not trusted:
            anomalies.append(
                {
                    "roblox_pid": row.get("pid"),
                    "parent_name": parent.get("name"),
                    "parent_exe": parent.get("exe"),
                    "reason": "roblox_not_launched_from_trusted_parent",
                }
            )
    return {
        "chains": chains[:6],
        "anomalies": anomalies[:8],
        "launch_provenance_anomaly": bool(anomalies),
    }


def _scan_memory_regions(pid: int) -> list[dict[str, Any]]:
    """Detect private committed regions that are both writable and executable."""
    suspicious: list[dict[str, Any]] = []
    if platform.system() != "Windows":
        return suspicious
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return suspicious

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    virtual_query_ex = kernel32.VirtualQueryEx
    virtual_query_ex.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCVOID,
        ctypes.POINTER(MEMORY_BASIC_INFORMATION),
        ctypes.c_size_t,
    ]
    virtual_query_ex.restype = ctypes.c_size_t

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    MEM_COMMIT = 0x1000
    MEM_PRIVATE = 0x20000
    handle = open_process(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, int(pid))
    if not handle:
        return suspicious
    try:
        address = 0
        max_address = 0x7FFFFFFFFFFF
        mbi = MEMORY_BASIC_INFORMATION()
        while address < max_address and len(suspicious) < 20:
            read = virtual_query_ex(handle, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi))
            if not read:
                break
            region_size = int(mbi.RegionSize or 0)
            if region_size <= 0:
                break
            protect = int(mbi.Protect or 0)
            executable = protect in {0x10, 0x20, 0x40, 0x80, 0xE0, 0x100, 0x120, 0x140, 0x180}
            writable = protect in {0x04, 0x08, 0x40, 0x80, 0xE0, 0x100, 0x120, 0x140, 0x180}
            if (
                int(mbi.State or 0) == MEM_COMMIT
                and int(mbi.Type or 0) == MEM_PRIVATE
                and executable
                and writable
                and region_size >= 4096
            ):
                suspicious.append(
                    {
                        "pid": pid,
                        "base_address": hex(address),
                        "size_bytes": region_size,
                        "protect": protect,
                        "reason": "private_executable_writable_region",
                    }
                )
            address += region_size
    finally:
        close_handle(handle)
    return suspicious[:20]


def _scan_module_trust(
    roblox_rows: list[dict[str, Any]],
    *,
    win_authenticode_status: Callable[[str], str],
    executor_label_matcher: Callable[[str], list[str]] | None = None,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in roblox_rows:
        pid = int(row["pid"])
        module_paths: list[str] = []
        try:
            proc = psutil.Process(pid)
            map_count = 0
            for mmap in proc.memory_maps(grouped=False):
                map_count += 1
                if map_count > 800:
                    break
                path = getattr(mmap, "path", "") or ""
                if path and not path.startswith("["):
                    module_paths.append(path)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            module_paths = []
        seen: set[str] = set()
        for path in module_paths:
            norm = path.replace("/", "\\")
            low = norm.lower()
            if low in seen or not low.endswith((".dll", ".exe")):
                continue
            seen.add(low)
            trusted = any(frag in low for frag in ROBLOX_MODULE_TRUSTED_FRAGMENTS)
            auth = win_authenticode_status(norm)
            labels = executor_label_matcher(norm) if executor_label_matcher else []
            if labels:
                failures.append(
                    {
                        "pid": pid,
                        "module_path": norm,
                        "authenticode_status": auth,
                        "executor_labels": labels,
                        "reason": "known_executor_module_in_roblox",
                        "confidence_hint": 0.94,
                    }
                )
                continue
            if trusted:
                continue
            if auth in {"Valid"}:
                continue
            if any(frag in low for frag in ("\\temp\\", "\\downloads\\", "\\desktop\\")) or (
                "\\users\\" in low and "\\appdata\\" in low and "\\roblox\\" not in low
            ):
                failures.append(
                    {
                        "pid": pid,
                        "module_path": norm,
                        "authenticode_status": auth,
                        "reason": "unsigned_module_in_roblox",
                        "confidence_hint": 0.82 if auth == "NotSigned" else 0.72,
                    }
                )
    return failures[:40]


def _scan_external_handle_proxy(roblox_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Best-effort user-mode proxy for external processes with risky access patterns."""
    if not roblox_rows:
        return []
    roblox_pids = {int(row["pid"]) for row in roblox_rows}
    roblox_started = min(float(row.get("create_time") or 0) for row in roblox_rows if row.get("create_time"))
    hits: list[dict[str, Any]] = []
    script = (
        "$rob=@(" + ",".join(str(pid) for pid in sorted(roblox_pids)) + ");"
        "$names=@('OpenProcess','WriteProcessMemory','NtWriteVirtualMemory','ReadProcessMemory');"
        "$out=@();"
        "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | ForEach-Object {"
        "  if($rob -contains $_.ProcessId){return};"
        "  $cmd=[string]$_.CommandLine;"
        "  if(-not $cmd){return};"
        "  foreach($n in $names){ if($cmd -match [regex]::Escape($n)){"
        "    $out += [pscustomobject]@{ pid=$_.ProcessId; name=$_.Name; cmd=$cmd.Substring(0,[Math]::Min(420,$cmd.Length)); reason='commandline_memory_api_reference' };"
        "    break"
        "  }};"
        "  foreach($pid in $rob){ if($cmd -match \"\\b$pid\\b\"){"
        "    $out += [pscustomobject]@{ pid=$_.ProcessId; name=$_.Name; cmd=$cmd.Substring(0,[Math]::Min(420,$cmd.Length)); reason='commandline_references_roblox_pid'; target_pid=$pid };"
        "  }};"
        "};"
        "$out | ConvertTo-Json -Compress"
    )
    raw = _run_command(["powershell", "-NoProfile", "-Command", script], timeout=14)
    if not raw.startswith("Unavailable:"):
        try:
            parsed = json.loads(raw)
            rows = parsed if isinstance(parsed, list) else [parsed] if isinstance(parsed, dict) else []
            for row in rows:
                if isinstance(row, dict):
                    hits.append(row)
        except json.JSONDecodeError:
            pass

    for proc in psutil.process_iter(["pid", "name", "exe", "create_time", "cmdline"]):
        try:
            info = proc.info
            pid = int(info["pid"])
            if pid in roblox_pids:
                continue
            name = str(info.get("name") or "").lower()
            if name in ROBLOX_PROCESS_NAMES:
                continue
            exe = str(info.get("exe") or "").lower()
            if not exe or any(marker in exe for marker in ("\\windows\\", "\\program files\\")):
                continue
            create_time = float(info.get("create_time") or 0)
            if roblox_started and create_time and abs(create_time - roblox_started) <= 180:
                if any(token in exe for token in ("executor", "inject", "cheat", "exploit", "hack")):
                    hits.append(
                        {
                            "pid": pid,
                            "name": info.get("name"),
                            "exe": info.get("exe"),
                            "reason": "suspicious_process_started_near_roblox",
                        }
                    )
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, ValueError):
            continue
    return hits[:20]


def _scan_driver_inventory() -> list[dict[str, Any]]:
    if platform.system() != "Windows":
        return []
    raw = _run_command(
        ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_SystemDriver | Select-Object Name,State,PathName | ConvertTo-Json -Compress"],
        timeout=14,
        max_chars=24000,
    )
    if raw.startswith("Unavailable:"):
        return []
    try:
        parsed = json.loads(raw)
        rows = parsed if isinstance(parsed, list) else [parsed] if isinstance(parsed, dict) else []
    except json.JSONDecodeError:
        return []
    suspicious: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Name") or "")
        path = str(row.get("PathName") or "")
        low = f"{name} {path}".lower()
        if not low.strip():
            continue
        if any(keyword in low for keyword in SUSPICIOUS_DRIVER_KEYWORDS):
            suspicious.append(
                {
                    "name": name,
                    "path": path[:520],
                    "state": row.get("State"),
                    "reason": "driver_keyword_match",
                }
            )
            continue
        if path and "\\windows\\system32\\drivers\\" not in low.replace("/", "\\"):
            suspicious.append(
                {
                    "name": name,
                    "path": path[:520],
                    "state": row.get("State"),
                    "reason": "nonstandard_driver_path",
                }
            )
    return suspicious[:30]


def roblox_runtime_provenance_scan(
    *,
    win_authenticode_status: Callable[[str], str],
    executor_label_matcher: Callable[[str], list[str]] | None = None,
) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Roblox runtime provenance scan is Windows-only"}

    roblox_rows = _find_roblox_processes()
    launch = _scan_launch_provenance(roblox_rows)
    memory_regions: list[dict[str, Any]] = []
    for row in roblox_rows[:2]:
        memory_regions.extend(_scan_memory_regions(int(row["pid"])))

    module_trust = _scan_module_trust(
        roblox_rows,
        win_authenticode_status=win_authenticode_status,
        executor_label_matcher=executor_label_matcher,
    )
    external_handles = _scan_external_handle_proxy(roblox_rows)
    drivers = _scan_driver_inventory()

    return {
        "available": True,
        "live_process_detected": bool(roblox_rows),
        "roblox_processes": roblox_rows,
        "launch_provenance": launch,
        "launch_provenance_anomaly": launch.get("launch_provenance_anomaly"),
        "suspicious_memory_regions": memory_regions,
        "module_trust_failures": module_trust,
        "external_process_handles": external_handles,
        "suspicious_drivers": drivers,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Runtime provenance complements offline artifacts: private RWX regions, unsigned in-process modules, "
            "nonstandard drivers, and external processes referencing Roblox memory APIs or PID."
        ),
    }
