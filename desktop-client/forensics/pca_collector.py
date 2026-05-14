from __future__ import annotations

import json
from typing import Any, Callable

RunCommand = Callable[..., str]

_PCA_SCRIPT = r"""
$start = (Get-Date).AddDays(-14)
$events = @()
try {
  $events = Get-WinEvent -FilterHashtable @{
    LogName='Microsoft-Windows-Program-Compatibility-Assistant/Operational'
    StartTime=$start
  } -MaxEvents 180 -ErrorAction SilentlyContinue |
  ForEach-Object {
    $xml = [xml]$_.ToXml()
    $app = ($xml.Event.EventData.Data | Where-Object { $_.Name -eq 'ProgramId' }).'#text'
    [pscustomobject]@{
      TimeCreated = $_.TimeCreated.ToUniversalTime().ToString('o')
      Id = $_.Id
      Level = $_.LevelDisplayName
      ProgramId = $app
      Message = if ($_.Message.Length -gt 900) { $_.Message.Substring(0,900) } else { $_.Message }
    }
  }
} catch {}
$events | ConvertTo-Json -Depth 4 -Compress
"""


def collect_pca_program_ids(run_command: RunCommand) -> dict[str, Any]:
    raw = run_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _PCA_SCRIPT],
        timeout=28,
        max_chars=120_000,
    )
    if raw.startswith("Unavailable:"):
        return {"available": False, "error": raw, "events": []}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"available": True, "parse_error": True, "events": [], "raw_head": raw[:2000]}
    rows = data if isinstance(data, list) else [data]
    events: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        pid = row.get("ProgramId") or ""
        events.append(
            {
                "time_created": row.get("TimeCreated"),
                "id": row.get("Id"),
                "level": row.get("Level"),
                "program_id": str(pid)[:520],
                "message_head": str(row.get("Message", ""))[:900],
            }
        )
    return {"available": True, "events": events, "count": len(events)}
