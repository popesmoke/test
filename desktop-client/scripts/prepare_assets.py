"""Extract scanner icon PNG/ICO from the embedded logo in app.py (used at build time)."""
from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from app import embedded_logo_data  # noqa: WPS433

    ASSETS.mkdir(parents=True, exist_ok=True)
    png_path = ASSETS / "scanner-icon.png"
    png_bytes = base64.b64decode(embedded_logo_data())
    png_path.write_bytes(png_bytes)

    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed; PNG written but ICO skipped (install requirements-build.txt).")
        return 0

    image = Image.open(png_path).convert("RGBA")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_path = ASSETS / "scanner-icon.ico"
    image.save(ico_path, format="ICO", sizes=sizes)
    print(f"Wrote {png_path}")
    print(f"Wrote {ico_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
