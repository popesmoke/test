#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo ""
echo "Secure build: Nuitka native .app bundle"
echo ""

if [[ -z "${DNG_API_URL:-}" && -z "${DIAGNOSTIC_API_URL:-}" ]]; then
  echo "Set DNG_API_URL before building, e.g.:"
  echo "  export DNG_API_URL=https://your-api.onrender.com"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found."
  exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip -q
.venv/bin/pip install -r requirements-build.txt -q
.venv/bin/python scripts/generate_build_config.py

DATA_ARG=()
if [[ -d assets ]]; then
  DATA_ARG=(--include-data-dir=assets=assets)
fi

echo "Compiling with Nuitka (may take several minutes)..."
.venv/bin/python -m nuitka app.py \
  --standalone \
  --assume-yes-for-downloads \
  --remove-output \
  --output-dir=dist-secure \
  --macos-create-app-bundle \
  --macos-app-name=dngscanner \
  --enable-plugin=tk-inter \
  --include-module=embedded_build_config \
  --include-module=runtime_config \
  --python-flag=no_docstrings \
  "${DATA_ARG[@]}"

echo ""
echo "Secure app bundle in: dist-secure/"
echo ""
