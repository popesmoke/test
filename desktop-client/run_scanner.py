"""Run the scanner from source (uses patched scanner_main.py when present)."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
entry = ROOT / "scanner_main.py"
if not entry.is_file():
    entry = ROOT / "app.py"

if __name__ == "__main__":
    runpy.run_path(str(entry), run_name="__main__")
