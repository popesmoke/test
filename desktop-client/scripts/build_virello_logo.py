"""Build Virello Scanner logo: red icon, transparent background, updated wordmark."""
from __future__ import annotations

import base64
import re
import sys
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
SOURCE = (
    REPO.parent
    / "assets"
    / "c__Users_proga_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_imagevir-b7054f76-3323-4b03-84d2-3d1ecc646f60.png"
)
# When run from Cursor workspace, source may live under .cursor/projects/.../assets
CURSOR_SOURCE = Path(
    r"C:\Users\proga\.cursor\projects\c-Users-proga-Documents-Codex-2026-05-10-project-secure-remote-system-diagnostic-system"
    r"\assets\c__Users_proga_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_imagevir-b7054f76-3323-4b03-84d2-3d1ecc646f60.png"
)


def resolve_source() -> Path:
    for candidate in (SOURCE, CURSOR_SOURCE):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Virello source logo not found")


def is_background(r: int, g: int, b: int, a: int) -> bool:
    if a < 8:
        return True
    return max(r, g, b) < 28 and abs(r - g) < 12 and abs(g - b) < 12


def is_blue_accent(r: int, g: int, b: int, a: int) -> bool:
    if a < 16:
        return False
    return b > 90 and b > r + 25 and b > g + 10


def blue_to_red(r: int, g: int, b: int) -> tuple[int, int, int]:
    strength = min(255, int(b * 1.05))
    red = max(r, strength)
    green = min(g, max(18, int(g * 0.35)))
    blue_channel = min(b, max(24, int(b * 0.22)))
    return red, green, blue_channel


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

    # Remove old "VIRELLO" wordmark (lower band) while keeping icon above ~y=620
    text_top = int(height * 0.72)
    for y in range(text_top, height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 0 and r > 170 and g > 170 and b > 170:
                pixels[x, y] = (0, 0, 0, 0)

    draw = ImageDraw.Draw(img)
    font = None
    for family, size in (
        ("Segoe UI", 62),
        ("Arial", 58),
        ("DejaVu Sans", 58),
    ):
        try:
            font = ImageFont.truetype(family, size=size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    label = "VIRELLO SCANNER"
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (width - text_w) // 2
    text_y = text_top + (height - text_top - text_h) // 2 - 8
    draw.text((text_x, text_y), label, font=font, fill=(255, 255, 255, 255))
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
