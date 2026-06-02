"""Strip solid background from the Virello logo source PNG and publish app/dashboard assets."""
from __future__ import annotations

import base64
import re
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
CURSOR_ASSETS = Path(
    r"C:\Users\proga\.cursor\projects\c-Users-proga-Documents-Codex-2026-05-10-project-secure-remote-system-diagnostic-system\assets"
)


def resolve_source() -> Path:
    search_dirs = [CURSOR_ASSETS, REPO / "assets", REPO.parent / "assets"]
    candidates: list[Path] = []
    for folder in search_dirs:
        if not folder.is_dir():
            continue
        candidates.extend(folder.glob("*.png"))
    if candidates:
        return max(candidates, key=lambda path: path.stat().st_mtime)
    raise FileNotFoundError("Virello source logo not found")


def is_background(r: int, g: int, b: int, a: int) -> bool:
    if a < 8:
        return True
    if max(r, g, b) < 32 and abs(r - g) < 14 and abs(g - b) < 14:
        return True
    return False


def is_red_accent(r: int, g: int, b: int, a: int) -> bool:
    if a < 16:
        return False
    return r > 70 and r > g + 12 and r > b + 12


def remove_bottom_right_marks(img: Image.Image) -> None:
    """Drop generator watermarks (sparkle marks) tucked in the bottom-right corner."""
    pixels = img.load()
    width, height = img.size
    x_start = int(width * 0.72)
    y_start = int(height * 0.72)
    for y in range(y_start, height):
        for x in range(x_start, width):
            r, g, b, a = pixels[x, y]
            if a < 16 or is_red_accent(r, g, b, a):
                continue
            pixels[x, y] = (0, 0, 0, 0)


def remove_background(source: Path) -> Image.Image:
    img = Image.open(source).convert("RGBA")
    pixels = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if is_background(r, g, b, a):
                pixels[x, y] = (0, 0, 0, 0)
    remove_bottom_right_marks(img)
    return img


def embed_logo_b85(png_bytes: bytes) -> str:
    compressed = zlib.compress(png_bytes, level=9)
    return base64.b85encode(compressed).decode("ascii")


def format_b85_literal(data: str, indent: str = "    ", line_width: int = 96) -> str:
    chunks = [data[i : i + line_width] for i in range(0, len(data), line_width)]
    lines = ["EMBEDDED_LOGO_B85 = ("]
    for chunk in chunks:
        lines.append(f'{indent}"{chunk}"')
    lines.append(")")
    return "\n".join(lines)


def patch_app_py(app_path: Path, b85: str) -> None:
    text = app_path.read_text(encoding="utf-8")
    pattern = re.compile(r"EMBEDDED_LOGO_B85 = \([\s\S]*?\)\n\n\ndef embedded_logo_data", re.MULTILINE)
    replacement = format_b85_literal(b85) + "\n\n\ndef embedded_logo_data"
    if not pattern.search(text):
        raise RuntimeError("Could not locate EMBEDDED_LOGO_B85 in app.py")
    app_path.write_text(pattern.sub(replacement, text), encoding="utf-8")


def main() -> int:
    source = resolve_source()
    logo = remove_background(source)

    web_assets = REPO / "web-dashboard" / "public" / "assets"
    web_assets.mkdir(parents=True, exist_ok=True)
    web_path = web_assets / "virello-scanner-logo.png"
    logo.save(web_path, format="PNG")

    desktop_assets = ROOT / "assets"
    desktop_assets.mkdir(parents=True, exist_ok=True)
    png_path = desktop_assets / "scanner-icon.png"
    logo.save(png_path, format="PNG")

    ico_path = desktop_assets / "scanner-icon.ico"
    icon = logo.copy()
    icon.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    b85 = embed_logo_b85(png_path.read_bytes())
    patch_app_py(ROOT / "app.py", b85)

    print(f"Source: {source}")
    print(f"Wrote {web_path}")
    print(f"Wrote {png_path}")
    print(f"Wrote {ico_path}")
    print("Updated embedded logo in app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
