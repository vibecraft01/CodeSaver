"""CodeSaver Desktop application entry point."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def _configure_qt_plugin_path() -> None:
    """Point Qt to bundled or installed PyQt5 plugins before QApplication starts."""
    import PyQt5
    from PyQt5.QtCore import QCoreApplication

    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    installed_root = Path(PyQt5.__file__).resolve().parent
    candidates = (
        bundle_root / "PyQt5" / "Qt5" / "plugins",
        bundle_root / "Qt5" / "plugins",
        installed_root / "Qt5" / "plugins",
    )
    for plugin_path in candidates:
        platforms_path = plugin_path / "platforms"
        if platforms_path.is_dir():
            os.environ["QT_PLUGIN_PATH"] = str(plugin_path)
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms_path)
            QCoreApplication.setLibraryPaths([str(plugin_path), *QCoreApplication.libraryPaths()])
            return


def main() -> int:
    if sys.version_info < (3, 10):
        print("CodeSaver Desktop requires Python 3.10 or newer.", file=sys.stderr)
        return 2
    _configure_qt_plugin_path()
    from PyQt5.QtWidgets import QApplication

    if __package__:
        from .main_window import MainWindow
    else:
        from desktop.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("CodeSaver Desktop")
    app.setOrganizationName("CodeSaver")
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
