from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from tkinter import BOTH, DISABLED, END, LEFT, NORMAL, StringVar, Tk, ttk, messagebox

import psutil
import requests

API_URL = os.getenv("DIAGNOSTIC_API_URL", "https://test-v7a8.onrender.com").rstrip("/")
CONSENT_VERSION = "2026-05-10.local-demo"

SCAN_STAGES = [
    "System Information Scan",
    "Application Environment Check",
    "Roblox Diagnostic Scan",
    "Approved Log Collection",
    "Process Overview Snapshot",
    "Package and Upload",
]

COLLECTED_CATEGORIES = [
    "Operating system and hardware summary",
    "CPU, memory, disk, and boot-time resource summary",
    "Installed application summary where available",
    "Roblox installation and approved diagnostic logs if present, including user IDs, usernames, place IDs, and LoadClientSettings lines found in logs",
    "Most recent item in Trash/Recycle Bin where available",
    "Windows Prefetch file metadata where available",
    "Windows Amcache metadata and BAM registry entries where available",
    "Recent Windows Event Log summaries and exported XML event-log file metadata where available",
    "Known Roblox executor indicator names in common app/log locations and traceback logs",
    "Running process name snapshot with PIDs and publishers omitted",
    "Hashed hostname and hardware UUID identifiers for session correlation",
]

EXECUTOR_NAMES = [
    "Volt",
    "Potassium",
    "Wave",
    "Seliware",
    "Synapse Z",
    "Madium",
    "Velocity",
    "SirHurt",
    "Solara",
    "Xeno",
    "RbxCli",
    "Ronin",
    "Matcha",
    "Matrix Hub",
    "Photon",
    "DX9WARE V2",
    "Serotonin",
    "Severe",
    "MacSploit",
    "Opiumware",
    "Delta",
    "Cryptic",
    "Vega X",
    "Codex",
]


def hashed_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def run_command(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
        return (result.stdout or result.stderr).strip()[:8000]
    except Exception as exc:
        return f"Unavailable: {exc}"


def hardware_identifiers() -> dict:
    system = platform.system()
    result = {"hardware_model": platform.machine(), "uuid_hash": None, "uuid_source": "unavailable"}
    if system == "Windows":
        model = run_command(["wmic", "computersystem", "get", "model", "/value"])
        uuid = run_command(["wmic", "csproduct", "get", "uuid", "/value"])
        result["hardware_model"] = model.replace("Model=", "").strip() or result["hardware_model"]
        raw_uuid = uuid.replace("UUID=", "").strip()
        if raw_uuid:
            result["uuid_hash"] = hashed_identifier(raw_uuid)
            result["uuid_source"] = "wmic csproduct UUID"
    elif system == "Darwin":
        output = run_command(["system_profiler", "SPHardwareDataType"])
        model_match = re.search(r"Model Name:\s*(.+)", output)
        uuid_match = re.search(r"Hardware UUID:\s*([A-Fa-f0-9-]+)", output)
        if model_match:
            result["hardware_model"] = model_match.group(1).strip()
        if uuid_match:
            result["uuid_hash"] = hashed_identifier(uuid_match.group(1).strip())
            result["uuid_source"] = "macOS Hardware UUID"
    return result


def installed_apps_summary() -> dict:
    system = platform.system()
    if system == "Windows":
        output = run_command([
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
            "Select-Object -First 80 DisplayName,DisplayVersion,Publisher | ConvertTo-Json",
        ])
        return {"source": "Windows uninstall registry", "sample": output}
    if system == "Darwin":
        apps = []
        for folder in [Path("/Applications"), Path.home() / "Applications"]:
            if folder.exists():
                apps.extend(path.name for path in folder.glob("*.app"))
        return {"source": "macOS Applications folders", "sample": sorted(apps)[:80]}
    return {"source": "unsupported", "sample": []}


def most_recent_trash_item() -> dict:
    candidates: list[Path] = []
    if platform.system() == "Windows":
        candidates.extend(Path(drive) / "$Recycle.Bin" for drive in ["C:\\"])
    elif platform.system() == "Darwin":
        candidates.append(Path.home() / ".Trash")

    latest = None
    for folder in candidates:
        if not folder.exists():
            continue
        try:
            paths = [path for path in folder.rglob("*") if path.is_file()]
        except Exception:
            paths = []
        for path in paths:
            try:
                stat = path.stat()
                item = {
                    "name": path.name,
                    "location": str(path.parent),
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "size_bytes": stat.st_size,
                }
                if latest is None or item["modified"] > latest["modified"]:
                    latest = item
            except Exception:
                continue
    return latest or {"status": "No accessible Trash/Recycle Bin item found"}


def prefetch_metadata() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Windows Prefetch is only available on Windows"}

    folder = Path(os.getenv("SystemRoot", "C:\\Windows")) / "Prefetch"
    if not folder.exists():
        return {"available": False, "reason": "Prefetch folder not found"}

    items = []
    try:
        files = sorted(folder.glob("*.pf"), key=lambda path: path.stat().st_mtime, reverse=True)[:120]
    except Exception as exc:
        return {"available": False, "reason": str(exc)}

    for path in files:
        try:
            stat = path.stat()
            items.append(
                {
                    "name": path.name,
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "size_bytes": stat.st_size,
                }
            )
        except Exception:
            continue
    return {"available": True, "folder": str(folder), "count": len(items), "items": items}


def amcache_metadata() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Amcache is a Windows artifact"}

    path = Path(os.getenv("SystemRoot", "C:\\Windows")) / "AppCompat" / "Programs" / "Amcache.hve"
    if not path.exists():
        return {"available": False, "path": str(path), "reason": "Amcache hive not found"}

    try:
        stat = path.stat()
        return {
            "available": True,
            "path": str(path),
            "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "size_bytes": stat.st_size,
            "note": "Raw hive parsing is not performed by this prototype.",
        }
    except Exception as exc:
        return {"available": False, "path": str(path), "reason": str(exc)}


def bam_registry_entries() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "BAM is a Windows registry artifact"}

    script = (
        "$base='HKLM:\\SYSTEM\\CurrentControlSet\\Services\\bam\\State\\UserSettings';"
        "if(Test-Path $base){"
        "Get-ChildItem $base | ForEach-Object {"
        "$sid=$_.PSChildName;"
        "Get-ItemProperty $_.PSPath | Select-Object -Property * | ConvertTo-Json -Depth 2"
        "}"
        "} else { '[]' }"
    )
    output = run_command(["powershell", "-NoProfile", "-Command", script])
    return {
        "available": True,
        "source": "HKLM SYSTEM CurrentControlSet Services bam State UserSettings",
        "raw_sample": output[:12000],
        "note": "BAM entries are reported as a bounded raw PowerShell JSON sample.",
    }


def windows_event_log_summary() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Windows Event Logs are only available on Windows"}

    script = (
        "$start=(Get-Date).AddDays(-7);"
        "Get-WinEvent -FilterHashtable @{LogName=@('Application','System'); StartTime=$start} "
        "-ErrorAction SilentlyContinue | "
        "Select-Object -First 120 TimeCreated,ProviderName,Id,LevelDisplayName,Message | "
        "ConvertTo-Json -Depth 3"
    )
    output = run_command(["powershell", "-NoProfile", "-Command", script])
    return {
        "available": True,
        "logs": ["Application", "System"],
        "window": "last 7 days",
        "raw_sample": output[:20000],
    }


def xml_event_log_files() -> dict:
    roots = []
    if platform.system() == "Windows":
        for env_name in ["USERPROFILE", "LOCALAPPDATA", "APPDATA"]:
            value = os.getenv(env_name)
            if value:
                roots.append(Path(value))
    else:
        roots.append(Path.home())

    items = []
    for root in roots:
        if not root.exists():
            continue
        try:
            matches = list(root.rglob("*.xml"))[:300]
        except Exception:
            matches = []
        for path in matches:
            lowered = path.name.lower()
            parent = str(path.parent).lower()
            if "event" not in lowered and "event" not in parent and "log" not in lowered:
                continue
            try:
                stat = path.stat()
                items.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "size_bytes": stat.st_size,
                    }
                )
            except Exception:
                continue
    items.sort(key=lambda item: item["modified"], reverse=True)
    return {"count": len(items[:80]), "items": items[:80]}


def executor_indicator_scan() -> dict:
    roots = []
    if platform.system() == "Windows":
        for env_name in ["LOCALAPPDATA", "APPDATA", "TEMP", "USERPROFILE"]:
            value = os.getenv(env_name)
            if value:
                roots.append(Path(value))
        roots.append(Path("C:\\Windows\\Prefetch"))
    elif platform.system() == "Darwin":
        roots.extend([Path.home() / "Library" / "Logs", Path.home() / "Library" / "Application Support", Path("/Applications")])
    else:
        roots.extend([Path.home()])

    patterns = {name: re.compile(re.escape(name).replace(r"\ ", r"[\s._-]*"), re.IGNORECASE) for name in EXECUTOR_NAMES}
    file_hits = []
    traceback_hits = []
    scanned_files = 0

    for root in roots:
        if not root.exists():
            continue
        try:
            paths = root.rglob("*")
            for path in paths:
                try:
                    if len(file_hits) >= 200 and len(traceback_hits) >= 80:
                        break
                    name_text = str(path)
                    matched = [name for name, pattern in patterns.items() if pattern.search(name_text)]
                    if matched:
                        stat = path.stat()
                        file_hits.append(
                            {
                                "matched_names": matched,
                                "path": str(path),
                                "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                                "is_file": path.is_file(),
                                "size_bytes": stat.st_size if path.is_file() else None,
                            }
                        )

                    if not path.is_file():
                        continue
                    scanned_files += 1
                    if path.suffix.lower() not in [".log", ".txt", ".traceback", ".json", ".xml"]:
                        continue
                    if path.stat().st_size > 2_000_000:
                        continue
                    text = path.read_text(errors="replace")
                    if "traceback" not in text.lower() and not any(pattern.search(text) for pattern in patterns.values()):
                        continue
                    lines = []
                    for line in text.splitlines():
                        if "traceback" in line.lower() or any(pattern.search(line) for pattern in patterns.values()):
                            lines.append(line.strip()[:500])
                        if len(lines) >= 12:
                            break
                    if lines:
                        traceback_hits.append({"path": str(path), "matched_lines": lines})
                except Exception:
                    continue
        except Exception:
            continue

    return {
        "executor_names_checked": EXECUTOR_NAMES,
        "roots_checked": [str(root) for root in roots],
        "scanned_text_files": scanned_files,
        "file_hits": file_hits[:200],
        "traceback_or_log_hits": traceback_hits[:80],
    }


def extract_roblox_signals(text: str) -> dict:
    user_ids = sorted(set(re.findall(r"\b(?:userId|UserId|userid|uid)[=: ]+(\d{3,})\b", text)))[:40]
    usernames = sorted(set(re.findall(r"\b(?:username|Username|userName|UserName)[=: ]+([A-Za-z0-9_]{3,20})\b", text)))[:40]
    place_ids = sorted(set(re.findall(r"\b(?:placeId|PlaceId|placeid)[=: ]+(\d{3,})\b", text)))[:40]
    load_client_settings = [
        line.strip()[:500]
        for line in text.splitlines()
        if "LoadClientSettings" in line
    ][:40]
    return {
        "user_ids": user_ids,
        "usernames": usernames,
        "place_ids": place_ids,
        "load_client_settings": load_client_settings,
    }


def roblox_diagnostics() -> dict:
    candidates: list[Path] = []
    if platform.system() == "Windows":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            candidates.append(Path(local_app_data) / "Roblox" / "logs")
    elif platform.system() == "Darwin":
        candidates.append(Path.home() / "Library" / "Logs" / "Roblox")

    logs = []
    for folder in candidates:
        if folder.exists():
            for path in sorted(folder.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
                try:
                    text = path.read_text(errors="replace")
                    logs.append(
                        {
                            "name": path.name,
                            "modified": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                            "signals": extract_roblox_signals(text),
                            "tail": text[-4000:],
                        }
                    )
                except Exception as exc:
                    logs.append({"name": path.name, "error": str(exc)})

    return {"detected": bool(logs), "log_locations_checked": [str(path) for path in candidates], "logs": logs}


def build_report() -> dict:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home().anchor or Path.home()))
    processes = []
    for proc in psutil.process_iter(["pid", "name", "username", "status"]):
        try:
            info = proc.info
            processes.append({"pid": info["pid"], "name": info["name"], "status": info["status"]})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_overview": {
            "os": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "hostname_hash": hashed_identifier(socket.gethostname()),
            "hardware": hardware_identifiers(),
        },
        "performance_environment": {
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "boot_time": datetime.fromtimestamp(psutil.boot_time(), timezone.utc).isoformat(),
            "installed_applications": installed_apps_summary(),
            "trash": most_recent_trash_item(),
            "prefetch": prefetch_metadata(),
        },
        "application_diagnostics": {"roblox": roblox_diagnostics()},
        "process_overview": {
            "count": len(processes),
            "items": sorted(processes, key=lambda item: (item["name"] or "").lower())[:250],
        },
        "security_integrity_signals": {
            "amcache": amcache_metadata(),
            "bam": bam_registry_entries(),
            "windows_event_logs": windows_event_log_summary(),
            "xml_event_log_files": xml_event_log_files(),
            "roblox_executor_indicators": executor_indicator_scan(),
        },
    }


class DiagnosticApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Secure Remote Diagnostic")
        self.root.geometry("760x560")
        self.pin = StringVar()
        self.status = StringVar(value="Ready")
        self.stage_labels: dict[str, ttk.Label] = {}
        self.progress = ttk.Progressbar(self.root, maximum=len(SCAN_STAGES), mode="determinate")
        self.build_welcome()

    def clear(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def build_welcome(self) -> None:
        self.clear()
        frame = ttk.Frame(self.root, padding=32)
        frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="Secure Remote Diagnostic", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text=(
                "This tool runs a one-time diagnostic scan only after you enter a support PIN "
                "and start the scan. It collects the categories below and uploads them to the reviewer session."
            ),
            wraplength=680,
        ).pack(anchor="w", pady=(16, 12))
        for item in COLLECTED_CATEGORIES:
            ttk.Label(frame, text=f"- {item}", wraplength=680).pack(anchor="w")
        ttk.Button(frame, text="Get Started", command=self.build_pin_screen).pack(anchor="w", pady=(24, 8))
        ttk.Button(frame, text="Join Discord / Support", command=lambda: messagebox.showinfo("Support", "Add your support link in desktop-client/app.py.")).pack(anchor="w")

    def build_pin_screen(self) -> None:
        self.clear()
        frame = ttk.Frame(self.root, padding=32)
        frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="Enter Session PIN", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Enter the PIN provided by your support technician or checker.").pack(anchor="w", pady=(8, 16))
        entry = ttk.Entry(frame, textvariable=self.pin, font=("Consolas", 18), width=12)
        entry.pack(anchor="w")
        entry.focus()
        ttk.Label(
            frame,
            text="By continuing, you confirm you understand the disclosed scan scope and want to submit the results.",
            wraplength=680,
        ).pack(anchor="w", pady=(18, 12))
        ttk.Button(frame, text="Start Scan", command=self.start_scan).pack(anchor="w")
        ttk.Button(frame, text="Back", command=self.build_welcome).pack(anchor="w", pady=(8, 0))

    def build_progress_screen(self) -> None:
        self.clear()
        frame = ttk.Frame(self.root, padding=32)
        frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="Diagnostic Scan", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, textvariable=self.status).pack(anchor="w", pady=(8, 16))
        self.progress = ttk.Progressbar(frame, maximum=len(SCAN_STAGES), mode="determinate", length=620)
        self.progress.pack(anchor="w", pady=(0, 18))
        self.stage_labels = {}
        for stage in SCAN_STAGES:
            label = ttk.Label(frame, text=f"{stage}: pending")
            label.pack(anchor="w", pady=3)
            self.stage_labels[stage] = label

    def set_stage(self, stage: str, state: str) -> None:
        self.stage_labels[stage].config(text=f"{stage}: {state}")
        self.root.update_idletasks()

    def start_scan(self) -> None:
        if not self.pin.get().strip():
            messagebox.showerror("PIN required", "Enter the session PIN provided by your checker.")
            return
        self.build_progress_screen()
        thread = threading.Thread(target=self.scan_and_upload, daemon=True)
        thread.start()

    def scan_and_upload(self) -> None:
        try:
            report = None
            for index, stage in enumerate(SCAN_STAGES, start=1):
                self.root.after(0, self.set_stage, stage, "running")
                if stage == "Package and Upload":
                    payload = {
                        "pin": self.pin.get().strip(),
                        "consent_version": CONSENT_VERSION,
                        "collected_categories": COLLECTED_CATEGORIES,
                        "report": report,
                    }
                    response = requests.post(f"{API_URL}/reports", json=payload, timeout=20)
                    response.raise_for_status()
                elif report is None and stage == "Process Overview Snapshot":
                    report = build_report()
                else:
                    time.sleep(0.4)
                self.root.after(0, self.set_stage, stage, "complete")
                self.root.after(0, self.progress.config, {"value": index})
            self.root.after(0, self.complete)
        except Exception as exc:
            self.root.after(0, self.fail, str(exc))

    def complete(self) -> None:
        self.status.set("Scan complete. Your results have been submitted.")
        messagebox.showinfo("Submitted", "Scan complete. Your results have been submitted.")

    def fail(self, error: str) -> None:
        self.status.set("Scan failed. No further collection is running.")
        messagebox.showerror("Scan failed", error)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    DiagnosticApp().run()
