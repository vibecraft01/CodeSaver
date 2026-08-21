"""Set the bundled PyQt5 platform-plugin path before any Qt import."""

from __future__ import annotations

import os
from pathlib import Path
import sys

bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
plugin_candidates = (
    bundle_root / "PyQt5" / "Qt5" / "plugins",
    bundle_root / "Qt5" / "plugins",
)
for plugin_path in plugin_candidates:
    platforms_path = plugin_path / "platforms"
    if platforms_path.is_dir():
        os.environ["QT_PLUGIN_PATH"] = str(plugin_path)
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms_path)
        break
