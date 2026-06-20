"""Zip the Nuitka standalone folder for one-file distribution (better AV profile than onefile EXE)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist-secure"


def find_app_dist() -> Path | None:
    if not DIST.exists():
        return None
    candidates = sorted(DIST.glob("*.dist"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def main() -> int:
    app_dist = find_app_dist()
    if not app_dist:
        print(f"No *.dist folder under {DIST}", file=sys.stderr)
        print(
            "package_release.py only zips a Nuitka standalone folder.\n"
            "For the normal single-file scanner EXE, run from desktop-client:\n"
            "  build-secure-exe.bat\n"
            "That produces dist-secure\\virello-scanner.exe\n"
            "For a portable folder + zip instead, run:\n"
            "  set DNG_STANDALONE=1\n"
            "  build-secure-exe.bat",
            file=sys.stderr,
        )
        return 1

    zip_base = DIST / "virello-scanner-portable"
    if zip_base.with_suffix(".zip").exists():
        zip_base.with_suffix(".zip").unlink()
    archive = shutil.make_archive(str(zip_base), "zip", root_dir=app_dist)
    print(f"Portable folder: {app_dist}")
    print(f"Distribution zip: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
