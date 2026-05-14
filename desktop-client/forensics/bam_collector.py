from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

RunCommand = Callable[..., str]

_BAM_SCRIPT = r"""
$base = 'HKLM:\SYSTEM\CurrentControlSet\Services\bam\State\UserSettings'
$rows = @()
if (Test-Path $base) {
  Get-ChildItem $base -ErrorAction SilentlyContinue | ForEach-Object {
    $sid = $_.PSChildName
    $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
    if ($null -eq $props) { return }
    $props.PSObject.Properties | Where-Object {
      $_.Name -notmatch '^PS' -and ($_.Name -match '[A-Za-z]:\\')
    } | ForEach-Object {
      $name = $_.Name
      $val = $_.Value
      $ticks = $null
      if ($val -is [byte[]] -and $val.Length -ge 8) {
        try { $ticks = [BitConverter]::ToInt64($val,0) } catch {}
      } elseif ($val -is [long] -or $val -is [int]) { $ticks = [int64]$val }
      $rows += [pscustomobject]@{ Sid=$sid; Path=$name; RawTicks=$ticks }
    }
  }
}
$rows | ConvertTo-Json -Depth 3 -Compress
"""


def collect_bam_execution_paths(run_command: RunCommand) -> dict[str, Any]:
    raw = run_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _BAM_SCRIPT],
        timeout=22,
        max_chars=100_000,
    )
    if raw.startswith("Unavailable:"):
        return {"available": False, "error": raw, "entries": []}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"available": True, "parse_error": True, "entries": [], "raw_head": raw[:2000]}
    rows = data if isinstance(data, list) else [data]
    entries: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        p = row.get("Path")
        if not p or not isinstance(p, str):
            continue
        if not re.search(r"[A-Za-z]:\\", p):
            continue
        entries.append({"sid": row.get("Sid"), "path": p, "raw_ticks": row.get("RawTicks")})
    return {"available": True, "entries": entries, "count": len(entries)}


def bam_path_basenames(entries: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for e in entries:
        p = e.get("path")
        if isinstance(p, str):
            out.add(norm_basename(p))
    return out


def norm_basename(path: str) -> str:
    try:
        return Path(path.replace("/", "\\")).name.lower()
    except Exception:
        return path.split("\\")[-1].lower()


def norm_exe_stem(path_or_name: str) -> str:
    """Match Prefetch base token (no extension) to BAM basename."""
    bn = norm_basename(path_or_name)
    for suf in (".exe", ".dll", ".sys", ".scr", ".com"):
        if bn.endswith(suf):
            return bn[: -len(suf)]
    return bn
