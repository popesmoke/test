"""Copy sources into _build_obf for Nuitka (native compile provides protection; no extra packers)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "_build_obf"


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )


def main() -> int:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scanner_src = ROOT / "scanner_main.py"
    app_src = scanner_src if scanner_src.is_file() else ROOT / "app.py"
    shutil.copy2(app_src, OUT_DIR / "app.py")
    shutil.copy2(ROOT / "runtime_config.py", OUT_DIR / "runtime_config.py")
    for module_name in ("evidence_engine.py", "roblox_runtime.py"):
        module_path = ROOT / module_name
        if module_path.is_file():
            shutil.copy2(module_path, OUT_DIR / module_name)

    virello_src = ROOT / "virello"
    if virello_src.is_dir():
        _copy_tree(virello_src, OUT_DIR / "virello")

    assets_src = ROOT / "assets"
    if assets_src.is_dir():
        assets_dst = OUT_DIR / "assets"
        assets_dst.mkdir(parents=True, exist_ok=True)
        for asset in assets_src.iterdir():
            if asset.is_file():
                shutil.copy2(asset, assets_dst / asset.name)
    print(f"Build entry: {OUT_DIR / 'app.py'}")
    if (OUT_DIR / "virello").is_dir():
        print(f"Included intelligence package: {OUT_DIR / 'virello'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
