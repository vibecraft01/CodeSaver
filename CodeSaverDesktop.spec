# -*- mode: python ; coding: utf-8 -*-
"""Portable PyInstaller definition for CodeSaver Desktop.

Build with:
    python -m PyInstaller --clean --noconfirm CodeSaverDesktop.spec
"""

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

project_dir = Path(SPECPATH).resolve()
entry_point = project_dir / "scripts" / "build_desktop_entry.py"
pyqt_datas, pyqt_binaries, pyqt_hiddenimports = collect_all("PyQt5")

a = Analysis(
    [str(entry_point)],
    pathex=[str(project_dir)],
    binaries=pyqt_binaries,
    datas=pyqt_datas,
    hiddenimports=collect_submodules("desktop") + pyqt_hiddenimports + ["PyQt5.sip"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project_dir / "scripts" / "qt_runtime_hook.py")],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CodeSaverDesktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="CodeSaverDesktop.app",
        icon=None,
        bundle_identifier="org.codesaver.desktop",
    )
