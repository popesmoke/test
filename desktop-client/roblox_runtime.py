"""Roblox runtime provenance: memory regions, module trust, drivers, launch chain, handle proxy."""
from __future__ import annotations

import json
import platform
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import psutil

RUNTIME_SCAN_BUDGET_SEC = 12.0
HANDLE_ENUM_MAX_ATTEMPTS = 96
HANDLE_ENUM_MAX_BUFFER_BYTES = 48 * 1024 * 1024
MEMORY_SCAN_MAX_ITERATIONS = 4096
DUPLICATE_SAME_ACCESS = 0x00000002

ROBLOX_PROCESS_NAMES = frozenset({"robloxplayerbeta.exe", "robloxplayer.exe", "roblox.exe"})
ROBLOX_TRUSTED_LAUNCHER_NAMES = frozenset(
    {
        "explorer.exe",
        "bloxstrap.exe",
        "fishstrap.exe",
        "robloxplayerbeta.exe",
        "robloxplayerlauncher.exe",
        "roblox.exe",
        "applicationframehost.exe",
        "shellexperiencehost.exe",
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
    "\\dotnet\\",
    "\\windowsapps\\",
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
    "iqvw64e",
    "iqvwd64e",
    "asrdrv",
    "physmem",
    "procexp",
    "kprocesshacker",
    "dbutil",
    "lenovo",
    "throttlestop",
    "hw64",
    "ene",
    "zam",
    "gmer",
)
# Process image stems commonly used by Roblox executors (2024–2026 landscape).
SUSPICIOUS_PROCESS_NAME_STEMS = frozenset(
    {
        "volt",
        "potassium",
        "wave",
        "synapse",
        "synapsez",
        "seliware",
        "madium",
        "cosmic",
        "velocity",
        "sirhurt",
        "solara",
        "xeno",
        "serotonin",
        "severe",
        "rbxcli",
        "lumen",
        "matcha",
        "matrixhub",
        "photon",
        "dx9ware",
        "delta",
        "vegax",
        "codex",
        "fluxus",
        "jjsploit",
        "hydrogen",
        "cryptic",
        "nucleus",
        "electronexecutor",
        "trigon",
        "ronix",
        "swift",
        "bunni",
        "evon",
        "awp",
        "chocosploit",
        "nihon",
        "nezur",
        "volcano",
        "zenith",
        "comet",
        "furku",
        "cryptonite",
        "scriptware",
        "script-ware",
        "krnl",
        "oxygen",
        "arceus",
    }
)
SUSPICIOUS_WINDOW_TITLE_KEYWORDS = (
    "executor",
    "script hub",
    "scripthub",
    "exploit",
    "injector",
    "autoexec",
    "synapse",
    "solara",
    "xeno",
    "wave",
    "volt",
    "delta",
    "potassium",
    "seliware",
    "roblox hack",
    "cheat menu",
)
TRUSTED_EXTERNAL_PROCESS_NAMES = frozenset(
    {
        "explorer.exe",
        "dwm.exe",
        "searchhost.exe",
        "startmenuexperiencehost.exe",
        "shellexperiencehost.exe",
        "applicationframehost.exe",
        "runtimebroker.exe",
        "svchost.exe",
        "csrss.exe",
        "wininit.exe",
        "winlogon.exe",
        "lsass.exe",
        "services.exe",
        "smss.exe",
        "system",
        "registry",
        "msmpeng.exe",
        "securityhealthservice.exe",
        "nvcontainer.exe",
        "nvdisplay.container.exe",
        "amdow.exe",
        "discord.exe",
        "steam.exe",
        "steamservice.exe",
        "epicgameslauncher.exe",
        "bloxstrap.exe",
        "fishstrap.exe",
        "robloxplayerlauncher.exe",
    }
)
# Dangerous cross-process access rights (WinNT.h).
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_CREATE_THREAD = 0x0002
PROCESS_DUP_HANDLE = 0x0040
PROCESS_VM_READ = 0x0010
HIGH_RISK_ACCESS_MASK = PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_CREATE_THREAD
RWX_HIGH_CONFIDENCE_MAX_BYTES = 2 * 1024 * 1024
RWX_MEDIUM_CONFIDENCE_MAX_BYTES = 8 * 1024 * 1024
RWX_JIT_NOISE_MIN_BYTES = 16 * 1024 * 1024


class _RuntimeScanBudget:
    def __init__(self, seconds: float = RUNTIME_SCAN_BUDGET_SEC) -> None:
        self._deadline = time.perf_counter() + max(1.0, seconds)

    def expired(self) -> bool:
        return time.perf_counter() >= self._deadline

    def remaining(self) -> float:
        return max(0.0, self._deadline - time.perf_counter())


def _runtime_scan_error(reason: str, *, partial: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "available": False,
        "reason": reason,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }
    if partial:
        payload.update(partial)
    return payload


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
                    "confidence": "medium",
                }
            )
    return {
        "chains": chains[:6],
        "anomalies": anomalies[:8],
        "launch_provenance_anomaly": bool(anomalies),
    }


def _region_has_pe_header(handle: int, address: int) -> bool:
    if platform.system() != "Windows" or not handle:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        read_process_memory = kernel32.ReadProcessMemory
        read_process_memory.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCVOID,
            wintypes.LPVOID,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        read_process_memory.restype = wintypes.BOOL
        buffer = (ctypes.c_char * 2)()
        read = ctypes.c_size_t(0)
        ok = read_process_memory(handle, ctypes.c_void_p(address), buffer, 2, ctypes.byref(read))
        return bool(ok and read.value >= 2 and buffer.raw[:2] == b"MZ")
    except (OSError, AttributeError, ImportError):
        return False


def _score_rwx_region(region_size: int, has_pe: bool) -> str:
    if region_size >= RWX_JIT_NOISE_MIN_BYTES and not has_pe:
        return "low"
    if has_pe or region_size <= RWX_HIGH_CONFIDENCE_MAX_BYTES:
        return "high"
    if region_size <= RWX_MEDIUM_CONFIDENCE_MAX_BYTES:
        return "medium"
    return "low"


def _scan_memory_regions(pid: int, *, budget: _RuntimeScanBudget | None = None) -> list[dict[str, Any]]:
    """Detect private committed regions that are both writable and executable."""
    suspicious: list[dict[str, Any]] = []
    if platform.system() != "Windows" or (budget and budget.expired()):
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
        iterations = 0
        while address < max_address and len(suspicious) < 20 and iterations < MEMORY_SCAN_MAX_ITERATIONS:
            if budget and budget.expired():
                break
            iterations += 1
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
                has_pe = False
                if region_size <= RWX_MEDIUM_CONFIDENCE_MAX_BYTES:
                    has_pe = _region_has_pe_header(int(handle), address)
                confidence = _score_rwx_region(region_size, has_pe)
                if confidence != "low":
                    suspicious.append(
                        {
                            "pid": pid,
                            "base_address": hex(address),
                            "size_bytes": region_size,
                            "protect": protect,
                            "reason": "private_executable_writable_region",
                            "has_pe_header": has_pe,
                            "confidence": confidence,
                        }
                    )
            address += max(region_size, 1)
    except Exception:
        return suspicious[:20]
    finally:
        close_handle(handle)
    suspicious.sort(key=lambda row: (0 if row.get("confidence") == "high" else 1, row.get("size_bytes", 0)))
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
        anonymous_maps = 0
        try:
            proc = psutil.Process(pid)
            for mmap in proc.memory_maps(grouped=False):
                path = getattr(mmap, "path", "") or ""
                if not path or path.startswith("["):
                    rss = int(getattr(mmap, "rss", 0) or 0)
                    if rss >= 65536:
                        anonymous_maps += 1
                    continue
                if not path.startswith("["):
                    module_paths.append(path)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            module_paths = []
        if anonymous_maps >= 3:
            failures.append(
                {
                    "pid": pid,
                    "module_path": "(anonymous/private image regions)",
                    "authenticode_status": "NotSigned",
                    "reason": "anonymous_executable_mappings_in_roblox",
                    "confidence_hint": 0.76,
                    "confidence": "medium",
                    "anonymous_region_count": anonymous_maps,
                }
            )
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
                        "confidence": "high",
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
                        "confidence": "high" if auth == "NotSigned" else "medium",
                    }
                )
    return failures[:40]


def _enumerate_roblox_process_handles(
    roblox_pids: set[int],
    *,
    budget: _RuntimeScanBudget | None = None,
) -> list[dict[str, Any]]:
    """User-mode handle table walk: external processes with VM write access to Roblox."""
    if platform.system() != "Windows" or not roblox_pids or (budget and budget.expired()):
        return []
    try:
        import ctypes
        from ctypes import wintypes

        ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

        ntdll = ctypes.WinDLL("ntdll")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        NtQuerySystemInformation = ntdll.NtQuerySystemInformation
        NtQuerySystemInformation.argtypes = [
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
        ]
        NtQuerySystemInformation.restype = ctypes.c_ulong

        class SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX(ctypes.Structure):
            _fields_ = [
                ("Object", ctypes.c_void_p),
                ("UniqueProcessId", ULONG_PTR),
                ("HandleValue", ULONG_PTR),
                ("GrantedAccess", wintypes.DWORD),
                ("CreatorBackTraceIndex", wintypes.USHORT),
                ("ObjectTypeIndex", wintypes.USHORT),
                ("HandleAttributes", wintypes.ULONG),
                ("Reserved", wintypes.ULONG),
            ]

        SystemExtendedHandleInformation = 64
        STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
        current_pid = int(kernel32.GetCurrentProcessId())
        buffer_size = 0x200000
        return_length = wintypes.ULONG(0)
        buffer = None
        status = STATUS_INFO_LENGTH_MISMATCH
        for _ in range(6):
            if budget and budget.expired():
                return []
            buffer = (ctypes.c_char * buffer_size)()
            status = NtQuerySystemInformation(
                SystemExtendedHandleInformation,
                buffer,
                buffer_size,
                ctypes.byref(return_length),
            )
            if status != STATUS_INFO_LENGTH_MISMATCH:
                break
            buffer_size = min(int(return_length.value) + 0x20000, HANDLE_ENUM_MAX_BUFFER_BYTES)
            if buffer_size >= HANDLE_ENUM_MAX_BUFFER_BYTES:
                return []
        if status != 0 or buffer is None:
            return []

        class HandleInfo(ctypes.Structure):
            _fields_ = [
                ("NumberOfHandles", ctypes.c_ulong),
                ("Reserved", ctypes.c_ulong),
            ]

        header = HandleInfo.from_buffer_copy(buffer)
        handle_count = int(header.NumberOfHandles)
        entry_size = ctypes.sizeof(SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX)
        offset = ctypes.sizeof(HandleInfo)

        duplicate_handle = kernel32.DuplicateHandle
        duplicate_handle.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.HANDLE),
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        duplicate_handle.restype = wintypes.BOOL
        get_process_id = kernel32.GetProcessId
        get_process_id.argtypes = [wintypes.HANDLE]
        get_process_id.restype = wintypes.DWORD
        close_handle = kernel32.CloseHandle
        open_process = kernel32.OpenProcess
        open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        open_process.restype = wintypes.HANDLE
        PROCESS_DUP_HANDLE = 0x0040

        pid_name_cache: dict[int, str] = {}
        owner_handles: dict[int, int] = {}
        hits: list[dict[str, Any]] = []
        seen_pairs: set[tuple[int, int]] = set()
        duplicate_attempts = 0

        for index in range(handle_count):
            if budget and budget.expired():
                break
            if len(hits) >= 24 or duplicate_attempts >= HANDLE_ENUM_MAX_ATTEMPTS:
                break
            entry_bytes = buffer[offset + index * entry_size : offset + (index + 1) * entry_size]
            if len(entry_bytes) < entry_size:
                break
            entry = SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX.from_buffer_copy(entry_bytes)
            owner_pid = int(entry.UniqueProcessId or 0)
            if owner_pid <= 4 or owner_pid == current_pid:
                continue
            access = int(entry.GrantedAccess or 0)
            if not (access & HIGH_RISK_ACCESS_MASK):
                continue
            handle_value = int(entry.HandleValue or 0)
            if not handle_value:
                continue
            pair_key = (owner_pid, handle_value)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            if owner_pid not in pid_name_cache:
                try:
                    pid_name_cache[owner_pid] = str(psutil.Process(owner_pid).name() or "").lower()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pid_name_cache[owner_pid] = ""
            owner_name = pid_name_cache[owner_pid]
            if owner_name in TRUSTED_EXTERNAL_PROCESS_NAMES or owner_name in ROBLOX_PROCESS_NAMES:
                continue

            owner_handle = owner_handles.get(owner_pid)
            if not owner_handle:
                owner_handle = open_process(PROCESS_DUP_HANDLE, False, owner_pid)
                if not owner_handle:
                    continue
                owner_handles[owner_pid] = int(owner_handle)

            duplicated = wintypes.HANDLE()
            duplicate_attempts += 1
            try:
                ok = duplicate_handle(
                    wintypes.HANDLE(owner_handle),
                    wintypes.HANDLE(handle_value),
                    kernel32.GetCurrentProcess(),
                    ctypes.byref(duplicated),
                    0,
                    False,
                    DUPLICATE_SAME_ACCESS,
                )
                if not ok or not duplicated.value:
                    continue
                target_pid = int(get_process_id(duplicated))
            except Exception:
                continue
            finally:
                if duplicated.value:
                    close_handle(duplicated)

            if target_pid not in roblox_pids:
                continue

            owner_brief = _resolve_process_brief(owner_pid)
            hits.append(
                {
                    "pid": owner_pid,
                    "name": owner_brief.get("name"),
                    "exe": owner_brief.get("exe"),
                    "target_roblox_pid": target_pid,
                    "granted_access": hex(access),
                    "reason": "cross_process_vm_access_to_roblox",
                    "detection_method": "handle_enumeration",
                    "confidence": "high",
                }
            )

        for proc_handle in owner_handles.values():
            try:
                close_handle(wintypes.HANDLE(proc_handle))
            except Exception:
                pass
        return hits
    except Exception:
        return []


def _scan_suspicious_nearby_processes(roblox_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not roblox_rows:
        return []
    roblox_pids = {int(row["pid"]) for row in roblox_rows}
    roblox_started = min(float(row.get("create_time") or 0) for row in roblox_rows if row.get("create_time"))
    hits: list[dict[str, Any]] = []
    for proc in psutil.process_iter(["pid", "name", "exe", "create_time", "cmdline"]):
        try:
            info = proc.info
            pid = int(info["pid"])
            if pid in roblox_pids:
                continue
            name = str(info.get("name") or "").lower()
            if name in ROBLOX_PROCESS_NAMES or name in TRUSTED_EXTERNAL_PROCESS_NAMES:
                continue
            exe = str(info.get("exe") or "").lower()
            stem = re.sub(r"[\s._-]+", "", Path(name or exe).stem.lower())
            if stem in SUSPICIOUS_PROCESS_NAME_STEMS:
                hits.append(
                    {
                        "pid": pid,
                        "name": info.get("name"),
                        "exe": info.get("exe"),
                        "reason": "known_executor_process_stem",
                        "detection_method": "process_name",
                        "confidence": "high",
                    }
                )
                continue
            create_time = float(info.get("create_time") or 0)
            if roblox_started and create_time and abs(create_time - roblox_started) <= 180:
                if any(token in exe for token in ("executor", "inject", "cheat", "exploit", "hack", "script")):
                    hits.append(
                        {
                            "pid": pid,
                            "name": info.get("name"),
                            "exe": info.get("exe"),
                            "reason": "suspicious_process_started_near_roblox",
                            "detection_method": "timing_heuristic",
                            "confidence": "medium",
                        }
                    )
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, ValueError):
            continue
    return hits[:20]

def _scan_suspicious_window_titles(roblox_pids: set[int], *, budget: _RuntimeScanBudget | None = None) -> list[dict[str, Any]]:
    if platform.system() != "Windows" or (budget and budget.expired()):
        return []
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return []

    user32 = ctypes.WinDLL("user32")
    get_window_thread_process_id = user32.GetWindowThreadProcessId
    get_window_thread_process_id.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    get_window_thread_process_id.restype = wintypes.DWORD
    is_window_visible = user32.IsWindowVisible
    get_window_text_length = user32.GetWindowTextLengthW
    get_window_text = user32.GetWindowTextW

    hits: list[dict[str, Any]] = []
    seen: set[int] = set()

    stop_enum = {"value": False}

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        try:
            if stop_enum["value"] or (budget and budget.expired()):
                return False
            if not is_window_visible(hwnd):
                return True
            length = get_window_text_length(hwnd)
            if length <= 0 or length > 512:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            get_window_text(hwnd, buffer, length + 1)
            title = buffer.value.strip()
            if not title:
                return True
            title_low = title.lower()
            if not any(keyword in title_low for keyword in SUSPICIOUS_WINDOW_TITLE_KEYWORDS):
                return True
            owner_pid = wintypes.DWORD(0)
            get_window_thread_process_id(hwnd, ctypes.byref(owner_pid))
            pid = int(owner_pid.value or 0)
            if not pid or pid in roblox_pids or pid in seen:
                return True
            seen.add(pid)
            if len(hits) >= 12:
                stop_enum["value"] = True
                return False
            try:
                proc = psutil.Process(pid)
                hits.append(
                    {
                        "pid": pid,
                        "name": proc.name(),
                        "exe": proc.exe(),
                        "window_title": title[:240],
                        "reason": "suspicious_window_title",
                        "detection_method": "window_title",
                        "confidence": "medium",
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                hits.append(
                    {
                        "pid": pid,
                        "window_title": title[:240],
                        "reason": "suspicious_window_title",
                        "detection_method": "window_title",
                        "confidence": "medium",
                    }
                )
            return True
        except Exception:
            return True

    try:
        user32.EnumWindows(callback, 0)
    except Exception:
        return hits
    return hits


def _scan_external_handle_proxy(
    roblox_rows: list[dict[str, Any]],
    *,
    budget: _RuntimeScanBudget | None = None,
) -> list[dict[str, Any]]:
    """Detect external processes with risky cross-process access to live Roblox."""
    if not roblox_rows or (budget and budget.expired()):
        return []
    roblox_pids = {int(row["pid"]) for row in roblox_rows}
    hits: list[dict[str, Any]] = []

    handle_hits = _enumerate_roblox_process_handles(roblox_pids, budget=budget)
    hits.extend(handle_hits)

    if not budget or not budget.expired():
        hits.extend(_scan_suspicious_nearby_processes(roblox_rows))
    if not budget or not budget.expired():
        hits.extend(_scan_suspicious_window_titles(roblox_pids, budget=budget))

    # Fallback: cmdline heuristics when handle enumeration is blocked (permissions/policy).
    if not handle_hits:
        script = (
            "$rob=@(" + ",".join(str(pid) for pid in sorted(roblox_pids)) + ");"
            "$names=@('OpenProcess','WriteProcessMemory','NtWriteVirtualMemory','ReadProcessMemory');"
            "$out=@();"
            "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | ForEach-Object {"
            "  if($rob -contains $_.ProcessId){return};"
            "  $cmd=[string]$_.CommandLine;"
            "  if(-not $cmd){return};"
            "  foreach($n in $names){ if($cmd -match [regex]::Escape($n)){"
            "    $out += [pscustomobject]@{ pid=$_.ProcessId; name=$_.Name; cmd=$cmd.Substring(0,[Math]::Min(420,$cmd.Length)); reason='commandline_memory_api_reference'; detection_method='commandline_heuristic'; confidence='low' };"
            "    break"
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

    deduped: list[dict[str, Any]] = []
    seen_pids: set[int] = set()
    for row in hits:
        pid = int(row.get("pid") or 0)
        if pid and pid in seen_pids:
            continue
        if pid:
            seen_pids.add(pid)
        deduped.append(row)
    return deduped[:24]


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
                    "confidence": "high",
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
                    "confidence": "medium",
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

    budget = _RuntimeScanBudget(RUNTIME_SCAN_BUDGET_SEC)
    try:
        roblox_rows = _find_roblox_processes()
        launch = _scan_launch_provenance(roblox_rows)
        memory_regions: list[dict[str, Any]] = []
        for row in roblox_rows[:2]:
            if budget.expired():
                break
            memory_regions.extend(_scan_memory_regions(int(row["pid"]), budget=budget))

        module_trust: list[dict[str, Any]] = []
        if not budget.expired():
            module_trust = _scan_module_trust(
                roblox_rows,
                win_authenticode_status=win_authenticode_status,
                executor_label_matcher=executor_label_matcher,
            )

        external_handles: list[dict[str, Any]] = []
        if not budget.expired():
            external_handles = _scan_external_handle_proxy(roblox_rows, budget=budget)

        drivers: list[dict[str, Any]] = []
        if not budget.expired():
            drivers = _scan_driver_inventory()

        high_confidence_memory = [row for row in memory_regions if row.get("confidence") == "high"]
        verified_handles = [row for row in external_handles if row.get("detection_method") == "handle_enumeration"]

        return {
            "available": True,
            "live_process_detected": bool(roblox_rows),
            "roblox_processes": roblox_rows,
            "launch_provenance": launch,
            "launch_provenance_anomaly": launch.get("launch_provenance_anomaly"),
            "suspicious_memory_regions": memory_regions,
            "high_confidence_memory_regions": high_confidence_memory,
            "module_trust_failures": module_trust,
            "external_process_handles": external_handles,
            "verified_external_handles": verified_handles,
            "suspicious_drivers": drivers,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "runtime_budget_exceeded": budget.expired(),
            "note": (
                "Runtime provenance complements offline artifacts: filtered private RWX regions (PE-aware), "
                "unsigned/injected modules, handle-table cross-process VM access, suspicious window titles, "
                "nonstandard drivers, and external processes referencing Roblox."
            ),
        }
    except Exception as exc:
        return _runtime_scan_error(
            f"Runtime provenance scan failed safely: {exc}",
            partial={"live_process_detected": False},
        )
