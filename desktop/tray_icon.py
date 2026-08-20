"""System tray integration with a small vector-style CodeSaver icon."""

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon


def create_icon() -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor("#58A6FF"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawRect(8, 6, 16, 20)
    painter.drawLine(11, 11, 21, 11)
    painter.drawLine(11, 16, 21, 16)
    painter.drawLine(11, 21, 18, 21)
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QObject):
    show_requested = pyqtSignal()
    backup_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self.tray = QSystemTrayIcon(create_icon(), parent)
        menu = QMenu()
        show_action = QAction("Show CodeSaver", menu)
        backup_action = QAction("Create backup", menu)
        quit_action = QAction("Quit", menu)
        show_action.triggered.connect(self.show_requested)
        backup_action.triggered.connect(self.backup_requested)
        quit_action.triggered.connect(self.quit_requested)
        menu.addAction(show_action)
        menu.addAction(backup_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._activated)

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_requested.emit()

    def show(self) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def notify(self, title: str, message: str, error: bool = False) -> None:
        if self.tray.isVisible():
            icon = QSystemTrayIcon.Critical if error else QSystemTrayIcon.Information
            self.tray.showMessage(title, message, icon, 5000)
