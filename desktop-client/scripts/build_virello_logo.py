"""Build logo from source art: transparent background, blue icon recolored to red, original wordmark kept."""
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
        candidates.extend(folder.glob("imagevir*.png"))
        candidates.extend(folder.glob("*virello*.png"))
    if not candidates:
        for folder in search_dirs:
            if folder.is_dir():
                candidates.extend(folder.glob("*.png"))
    if candidates:
        return max(candidates, key=lambda path: path.stat().st_mtime)
    raise FileNotFoundError("Virello source logo not found")


def is_background(r: int, g: int, b: int, a: int) -> bool:
    if a < 8:
        return True
    return max(r, g, b) < 28 and abs(r - g) < 12 and abs(g - b) < 12


def is_blue_accent(r: int, g: int, b: int, a: int) -> bool:
    if a < 16:
        return False
    if b > 90 and b > r + 20 and b > g + 8:
        return True
    return b > 55 and b >= max(r, g) + 10


def blue_to_red(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Map blue gradient tones to a matching red gradient."""
    red = min(255, int(b * 0.98 + r * 0.35))
    green = min(g, max(12, int(g * 0.32 + b * 0.04)))
    blue_out = min(b, max(18, int(b * 0.22 + r * 0.08)))
    return red, green, blue_out


def process_logo(source: Path) -> Image.Image:
    img = Image.open(source).convert("RGBA")
    pixels = img.load()
    width, height = img.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if is_background(r, g, b, a):
                pixels[x, y] = (0, 0, 0, 0)
            elif is_blue_accent(r, g, b, a):
                nr, ng, nb = blue_to_red(r, g, b)
                pixels[x, y] = (nr, ng, nb, a)
            # else: keep original pixels (white VIRELLO wordmark, anti-aliasing, etc.)

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
    logo = process_logo(source)

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

    png_bytes = png_path.read_bytes()
    b85 = embed_logo_b85(png_bytes)
    patch_app_py(ROOT / "app.py", b85)

    print(f"Source: {source}")
    print(f"Wrote {web_path}")
    print(f"Wrote {png_path}")
    print(f"Wrote {ico_path}")
    print("Updated embedded logo in app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
