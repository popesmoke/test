"""Copy sources into _build_obf for Nuitka (native compile provides protection; no extra packers)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "_build_obf"


def main() -> int:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "app.py", OUT_DIR / "app.py")
    shutil.copy2(ROOT / "runtime_config.py", OUT_DIR / "runtime_config.py")
    print(f"Build entry: {OUT_DIR / 'app.py'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
