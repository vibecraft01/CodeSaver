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
"$VENV_PYTHON" -m PyInstaller --clean --noconfirm --onefile --name CodeSaverDesktop scripts/build_desktop_entry.py

if command -v dpkg-deb >/dev/null 2>&1; then
    PACKAGE_ROOT=$(mktemp -d)
    trap 'rm -rf "$PACKAGE_ROOT"' EXIT
    mkdir -p "$PACKAGE_ROOT/DEBIAN" "$PACKAGE_ROOT/usr/bin"
    cp dist/CodeSaverDesktop "$PACKAGE_ROOT/usr/bin/codesaver-desktop"
    chmod 755 "$PACKAGE_ROOT/usr/bin/codesaver-desktop"
    cat > "$PACKAGE_ROOT/DEBIAN/control" <<'CONTROL'
Package: codesaver-desktop
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: CodeSaver Contributors
Description: CodeSaver Desktop graphical backup utility
CONTROL
    dpkg-deb --build "$PACKAGE_ROOT" CodeSaverDesktop-linux-amd64.deb >/dev/null
    echo "Built CodeSaverDesktop-linux-amd64.deb"
else
    echo "Built dist/CodeSaverDesktop (dpkg-deb not available for .deb packaging)."
fi
