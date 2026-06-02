"""Quick check that EMBEDDED_LOGO_B85 in app.py decodes to a PNG."""
from __future__ import annotations

import base64
import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    text = (ROOT / "app.py").read_text(encoding="utf-8")
    match = re.search(r"EMBEDDED_LOGO_B85 = \(([\s\S]*?)\)\n\n\ndef embedded_logo_data", text)
    if not match:
        print("EMBEDDED_LOGO_B85 block not found", file=sys.stderr)
        return 1
    chunks = re.findall(r'"([^"]*)"', match.group(1))
    payload = "".join(chunks)
    raw = zlib.decompress(base64.b85decode(payload.encode("ascii")))
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        print("Decoded payload is not a PNG", file=sys.stderr)
        return 1
    print(f"OK: embedded logo is {len(raw)} byte PNG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
