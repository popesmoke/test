from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

RunCommand = Callable[..., str]

_PE_HEADER = re.compile(rb"MZ.{0,4096}PE\0\0", re.DOTALL)


def sha256_file(path: Path, max_bytes: int = 2_000_000) -> str | None:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            remaining = max_bytes
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                h.update(chunk)
                remaining -= len(chunk)
        return h.hexdigest()
    except OSError:
        return None


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def file_entropy_sample(path: Path, sample: int = 262_144) -> float | None:
    try:
        with path.open("rb") as f:
            blob = f.read(sample)
        return round(shannon_entropy(blob), 4) if blob else None
    except OSError:
        return None


def is_pe_file(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            head = f.read(65536)
    except OSError:
        return False
    if not head.startswith(b"MZ"):
        return False
    return _PE_HEADER.search(head) is not None


def packed_pe_heuristic(path: Path, entropy: float | None) -> bool:
    if entropy is None or entropy < 7.2:
        return False
    if not is_pe_file(path):
        return False
    try:
        size = path.stat().st_size
    except OSError:
        return False
    if size < 20_000:
        return False
    return entropy >= 7.45


def batch_authenticode_status(paths: list[str], run_command: RunCommand) -> dict[str, dict[str, Any]]:
    """Map path -> {status, status_message, signer_subject} using PowerShell."""
    result: dict[str, dict[str, Any]] = {}
    if not paths:
        return result
    safe: list[str] = []
    for p in paths[:48]:
        p = p.strip()
        if not p or len(p) > 520:
            continue
        if p not in safe:
            safe.append(p)
    if not safe:
        return result
    payload_b64 = base64.b64encode(json.dumps(safe).encode("utf-8")).decode("ascii")
    script = (
        f"$paths = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{payload_b64}')) | ConvertFrom-Json;"
        "$out = @();"
        "foreach ($p in $paths) {"
        " try {"
        "  if (-not (Test-Path -LiteralPath $p)) { $out += [pscustomobject]@{Path=$p; Status='NotSigned'; StatusMessage='FileMissing'; Signer=$null}; continue }"
        "  $s = Get-AuthenticodeSignature -LiteralPath $p -ErrorAction Stop;"
        "  $sub = $null; if ($s.SignerCertificate) { $sub = $s.SignerCertificate.Subject };"
        "  $out += [pscustomobject]@{Path=$p; Status=$s.Status.ToString(); StatusMessage=$s.StatusMessage; Signer=$sub}"
        " } catch {"
        "  $out += [pscustomobject]@{Path=$p; Status='Error'; StatusMessage=$_.Exception.Message; Signer=$null}"
        " }"
        "};"
        "$out | ConvertTo-Json -Depth 4 -Compress"
    )
    raw = run_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], timeout=45, max_chars=120_000)
    if raw.startswith("Unavailable:"):
        return {p: {"status": "Unknown", "status_message": raw, "signer": None} for p in safe}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {p: {"status": "Unknown", "status_message": "json_parse_error", "signer": None} for p in safe}
    rows = parsed if isinstance(parsed, list) else [parsed]
    for row in rows:
        if not isinstance(row, dict):
            continue
        p = row.get("Path")
        if not p:
            continue
        result[str(p)] = {
            "status": str(row.get("Status", "Unknown")),
            "status_message": str(row.get("StatusMessage", ""))[:400],
            "signer": row.get("Signer"),
        }
    for p in safe:
        result.setdefault(p, {"status": "Unknown", "status_message": "not_in_batch_output", "signer": None})
    return result


def yara_scan_file(path: Path, rules_dir: Path | None) -> tuple[list[str], bool]:
    """Returns (match_rule_names, yara_runtime_available)."""
    try:
        import yara  # type: ignore
    except ImportError:
        return [], False
    rule_paths: list[Path] = []
    env_dir = os.getenv("FORENSICS_YARA_RULES")
    if env_dir:
        ed = Path(env_dir)
        if ed.is_dir():
            rule_paths.extend(ed.glob("*.yar"))
            rule_paths.extend(ed.glob("*.yara"))
    if rules_dir and rules_dir.is_dir():
        rule_paths.extend(rules_dir.glob("*.yar"))
        rule_paths.extend(rules_dir.glob("*.yara"))
    if not rule_paths:
        return [], True
    matches: list[str] = []
    try:
        rules = yara.compile(filepaths=[str(p) for p in rule_paths[:12]])
        for m in rules.match(str(path)):
            matches.append(m.rule)
    except Exception:
        return [], True
    return matches[:24], True


def is_removable_path(path: str) -> bool:
    p = path.upper().replace("/", "\\")
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        if p.startswith(f"{letter}:\\") and not p.startswith("C:\\"):
            return True
    return False


def is_tempish_path(path: str) -> bool:
    p = path.lower().replace("/", "\\")
    markers = (
        "\\temp\\",
        "\\tmp\\",
        "\\appdata\\local\\temp",
        "\\windows\\temp",
        "\\content.mso\\",
        "\\wintemp\\",
        "\\cache\\",
    )
    return any(m in p for m in markers)


def is_downloads_path(path: str) -> bool:
    p = path.lower().replace("/", "\\")
    return "\\downloads\\" in p or "\\download\\" in p or "discord" in p and "downloads" in p


def random_filename_score(name: str) -> float:
    stem = Path(name).stem
    if len(stem) < 10:
        return 0.0
    alnum = sum(1 for c in stem if c.isalnum())
    if alnum < 8:
        return 0.0
    letters = [c for c in stem if c.isalpha()]
    if not letters:
        return 0.0
    transitions = sum(1 for i in range(len(letters) - 1) if letters[i].islower() != letters[i + 1].islower())
    digit_ratio = sum(1 for c in stem if c.isdigit()) / max(len(stem), 1)
    score = 0.0
    if len(stem) >= 16 and digit_ratio <= 0.35 and transitions >= 8:
        score += 0.4
    if re.fullmatch(r"[A-Za-z0-9_-]{16,}", stem):
        score += 0.35
    if re.search(r"[0-9A-Fa-f]{8}", stem) and len(stem) >= 14:
        score += 0.25
    return min(score, 1.0)


def fake_extension_flags(name: str) -> list[str]:
    flags: list[str] = []
    lower = name.lower()
    if re.search(r"\.(jpg|jpeg|png|gif|txt|pdf)\.(exe|dll|bat|cmd|ps1|scr|com)\Z", lower):
        flags.append("document_extension_before_executable")
    if lower.count(".") >= 2 and re.search(r"\.(exe|dll)\Z", lower):
        parts = lower.split(".")
        if len(parts) >= 3 and parts[-2] in {"zip", "rar", "7z", "iso", "img", "dat", "log"}:
            flags.append("archive_like_inner_executable_name")
    return flags
