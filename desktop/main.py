"""CodeSaver Desktop application entry point."""

from __future__ import annotations

import sys
import os
from pathlib import Path


def _configure_qt_plugin_path() -> None:
    """Point Qt to PyQt5 plugins explicitly, including non-ASCII Windows paths."""
    import PyQt5
    from PyQt5.QtCore import QCoreApplication

    plugin_path = Path(PyQt5.__file__).resolve().parent / "Qt5" / "plugins"
    if plugin_path.is_dir():
        os.environ["QT_PLUGIN_PATH"] = str(plugin_path)
        QCoreApplication.addLibraryPath(str(plugin_path))


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
