#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
PYTHON_BIN=${PYTHON_BIN:-python3}
VENV_DIR="$PROJECT_DIR/.desktop-build-venv"
trap 'rm -rf "$VENV_DIR"' EXIT
"$PYTHON_BIN" -m venv "$VENV_DIR"
VENV_PYTHON="$VENV_DIR/bin/python"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -e ".[desktop,release]"
"$VENV_PYTHON" -m PyInstaller --clean --noconfirm --windowed --name CodeSaverDesktop scripts/build_desktop_entry.py
ditto -c -k --sequesterRsrc --keepParent "dist/CodeSaverDesktop.app" "CodeSaverDesktop-macos.zip"
echo "Built CodeSaverDesktop-macos.zip"
