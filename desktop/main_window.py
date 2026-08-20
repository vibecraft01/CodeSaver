"""Main CodeSaver Desktop window."""

from __future__ import annotations

from pathlib import Path
from shutil import disk_usage

from PyQt5.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from codesaver.core import BackupError

from .backup_manager import DesktopBackupManager
from .settings_dialog import SettingsDialog
from .tray_icon import TrayIcon
from .utils import DesktopSettings, archive_details, format_bytes, load_settings, save_settings

TEXT = {
    "ru": {
        "title": "CodeSaver Desktop",
        "open": "Открыть папку",
        "backup": "Создать бэкап",
        "restore": "Восстановить из бэкапа",
        "settings": "Настройки",
        "project": "Проект",
        "path": "Путь: —",
        "stats": "Файлов: 0 • Размер: 0 B",
        "archive": "Имя архива",
        "date": "Дата создания",
        "size": "Размер",
        "ready": "Готово",
        "choose_project": "Сначала выберите папку проекта.",
        "backup_started": "Создание бэкапа…",
        "backup_done": "Бэкап создан",
        "restore_done": "Восстановлено файлов: {count}",
        "error": "Ошибка",
        "confirm": "Подтверждение",
        "confirm_restore": "Восстановить архив и заменить существующие файлы?",
        "tray": "CodeSaver работает в фоне.",
        "disk_warning": "На диске осталось мало места: {free}",
    },
    "en": {
        "title": "CodeSaver Desktop",
        "open": "Open folder",
        "backup": "Create backup",
        "restore": "Restore backup",
        "settings": "Settings",
        "project": "Project",
        "path": "Path: —",
        "stats": "Files: 0 • Size: 0 B",
        "archive": "Archive name",
        "date": "Created",
        "size": "Size",
        "ready": "Ready",
        "choose_project": "Choose a project folder first.",
        "backup_started": "Creating backup…",
        "backup_done": "Backup created",
        "restore_done": "Files restored: {count}",
        "error": "Error",
        "confirm": "Confirmation",
        "confirm_restore": "Restore the archive and replace existing files?",
        "tray": "CodeSaver is running in the background.",
        "disk_warning": "Low disk space remaining: {free}",
    },
}


class BackupWorker(QThread):
    progress = pyqtSignal(int, int, int, int)
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self, manager: DesktopBackupManager, operation: str, archive: Path | None = None, language: str = "en"
    ) -> None:
        super().__init__()
        self.manager = manager
        self.operation = operation
        self.archive = archive
        self.language = language

    def run(self) -> None:
        try:
            if self.operation == "backup":
                archive = self.manager.create_backup(self._progress)
                self.succeeded.emit(str(archive))
            else:
                count = self.manager.restore_backup(self.archive, overwrite=True)
                self.succeeded.emit(str(count))
        except (BackupError, OSError, ValueError) as exc:
            self.failed.emit(exc.localized(self.language) if isinstance(exc, BackupError) else str(exc))

    def _progress(self, current: int, total: int, _path: Path, processed: int, total_bytes: int) -> None:
        self.progress.emit(current, total, processed, total_bytes)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings: DesktopSettings = load_settings()
        self.manager: DesktopBackupManager | None = None
        self.worker: BackupWorker | None = None
        self._operation = ""
        self._allow_close = False
        self.setMinimumSize(820, 560)
        self._build_ui()
        self._setup_tray()
        self._apply_theme()
        self._configure_autosave()
        if self.settings.project_dir and Path(self.settings.project_dir).is_dir():
            self._set_project(Path(self.settings.project_dir))

    def _text(self, key: str, **values: object) -> str:
        return TEXT[self.settings.language].get(key, key).format(**values)

    def _build_ui(self) -> None:
        self.setWindowTitle(self._text("title"))
        central = QWidget()
        layout = QVBoxLayout(central)
        project_frame = QFrame()
        project_layout = QVBoxLayout(project_frame)
        header = QHBoxLayout()
        self.project_header = QLabel()
        header.addWidget(self.project_header)
        header.addStretch()
        self.open_button = QPushButton(self._text("open"))
        self.open_button.clicked.connect(self._choose_project)
        header.addWidget(self.open_button)
        project_layout.addLayout(header)
        self.path_label = QLabel(self._text("path"))
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.stats_label = QLabel(self._text("stats"))
        project_layout.addWidget(self.path_label)
        project_layout.addWidget(self.stats_label)
        layout.addWidget(project_frame)

        actions = QHBoxLayout()
        self.backup_button = QPushButton(self._text("backup"))
        self.backup_button.clicked.connect(self._start_backup)
        self.restore_button = QPushButton(self._text("restore"))
        self.restore_button.clicked.connect(self._restore_selected)
        self.settings_button = QPushButton(self._text("settings"))
        self.settings_button.clicked.connect(self._open_settings)
        actions.addWidget(self.backup_button)
        actions.addWidget(self.restore_button)
        actions.addStretch()
        actions.addWidget(self.settings_button)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([self._text("archive"), self._text("date"), self._text("size")])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self._restore_selected())
        layout.addWidget(self.table, 1)

        progress_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_text = QLabel("0/0 • 0 B/0 B")
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.progress_text)
        layout.addLayout(progress_row)
        self.setCentralWidget(central)
        self._retranslate_ui()
        self.statusBar().showMessage(self._text("ready"))

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self._text("title"))
        self.project_header.setText(f"<b>{self._text('project')}</b>")
        self.open_button.setText(self._text("open"))
        self.backup_button.setText(self._text("backup"))
        self.restore_button.setText(self._text("restore"))
        self.settings_button.setText(self._text("settings"))
        self.table.setHorizontalHeaderLabels([self._text("archive"), self._text("date"), self._text("size")])

    def _setup_tray(self) -> None:
        self.tray = TrayIcon(self)
        self.tray.show_requested.connect(self._show_from_tray)
        self.tray.backup_requested.connect(self._start_backup)
        self.tray.quit_requested.connect(self._quit_from_tray)
        self.tray.show()

    def _apply_theme(self) -> None:
        if self.settings.theme == "dark":
            self.setStyleSheet(
                "QMainWindow,QWidget{background:#0D1117;color:#FFFFFF;}"
                "QFrame{border:1px solid #30363D;border-radius:6px;}"
                "QPushButton{background:#21262D;color:#FFFFFF;border:1px solid #30363D;"
                "padding:8px 14px;border-radius:5px;}"
                "QPushButton:hover{background:#30363D;border-color:#58A6FF;}"
                "QTableWidget{background:#161B22;gridline-color:#30363D;border:1px solid #30363D;}"
                "QHeaderView::section{background:#21262D;color:#FFFFFF;padding:6px;border:0;}"
                "QProgressBar{border:1px solid #30363D;border-radius:4px;text-align:center;}"
                "QProgressBar::chunk{background:#58A6FF;}"
            )
        else:
            self.setStyleSheet("QPushButton{padding:8px 14px;} QTableWidget{gridline-color:#D0D7DE;}")

    def _configure_autosave(self) -> None:
        if hasattr(self, "autosave_timer"):
            self.autosave_timer.stop()
        self.autosave_timer = QTimer(self)
        if self.settings.interval_minutes > 0:
            self.autosave_timer.timeout.connect(self._autosave)
            self.autosave_timer.start(self.settings.interval_minutes * 60 * 1000)

    def _choose_project(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, self._text("open"))
        if directory:
            self._set_project(Path(directory))

    def _set_project(self, path: Path) -> None:
        self.settings.project_dir = str(path.resolve())
        self.manager = DesktopBackupManager(path, self.settings)
        self.path_label.setText(str(path.resolve()))
        self._refresh_project_info()
        self._refresh_backups()
        save_settings(self.settings)
        self.statusBar().showMessage(self._text("ready"))

    def _refresh_project_info(self) -> None:
        if not self.manager:
            return
        try:
            files = self.manager.list_files()
            total = sum(path.stat().st_size for path in files)
            self.stats_label.setText(f"{self._text('stats').split(':')[0]}: {len(files)} • {format_bytes(total)}")
        except (BackupError, OSError) as exc:
            self._show_error(str(exc))

    def _refresh_backups(self) -> None:
        self.table.setRowCount(0)
        if not self.manager:
            return
        try:
            for row, (path, date, size) in enumerate(archive_details(self.manager.backup_dir)):
                self.table.insertRow(row)
                item = QTableWidgetItem(path.name)
                item.setData(Qt.UserRole, str(path))
                self.table.setItem(row, 0, item)
                self.table.setItem(row, 1, QTableWidgetItem(date))
                self.table.setItem(row, 2, QTableWidgetItem(size))
        except OSError as exc:
            self._show_error(str(exc))

    def _start_backup(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        if self.worker and self.worker.isRunning():
            return
        self._operation = "backup"
        self.progress.setValue(0)
        self.progress_text.setText("0/0 • 0 B/0 B")
        self.statusBar().showMessage(self._text("backup_started"))
        self._set_busy(True)
        self.worker = BackupWorker(self.manager, "backup", language=self.settings.language)
        self._connect_worker()
        self.worker.start()

    def _autosave(self) -> None:
        if self.manager and not (self.worker and self.worker.isRunning()):
            self._start_backup()

    def _restore_selected(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        row = self.table.currentRow()
        if row < 0:
            return
        archive = Path(self.table.item(row, 0).data(Qt.UserRole))
        answer = QMessageBox.question(self, self._text("confirm"), self._text("confirm_restore"))
        if answer != QMessageBox.Yes:
            return
        self._operation = "restore"
        self.statusBar().showMessage(self._text("backup_started"))
        self._set_busy(True)
        self.worker = BackupWorker(self.manager, "restore", archive, language=self.settings.language)
        self._connect_worker()
        self.worker.start()

    def _connect_worker(self) -> None:
        self.worker.progress.connect(self._update_progress)
        self.worker.succeeded.connect(self._worker_succeeded)
        self.worker.failed.connect(self._worker_failed)
        self.worker.finished.connect(lambda: self._set_busy(False))

    def _update_progress(self, current: int, total: int, processed: int, total_bytes: int) -> None:
        percent = 100 if total == 0 else int(current / total * 100)
        self.progress.setValue(percent)
        self.progress_text.setText(f"{current}/{total} • {format_bytes(processed)}/{format_bytes(total_bytes)}")

    def _worker_succeeded(self, value: str) -> None:
        if self._operation == "backup":
            self.progress.setValue(100)
            self.statusBar().showMessage(self._text("backup_done"))
            self.tray.notify(self._text("title"), self._text("backup_done"))
            if self.manager:
                free_space = disk_usage(self.manager.backup_dir).free
                if free_space < 100 * 1024 * 1024:
                    self.tray.notify(
                        self._text("error"), self._text("disk_warning", free=format_bytes(free_space)), error=True
                    )
        else:
            self.statusBar().showMessage(self._text("restore_done", count=value))
        self._refresh_project_info()
        self._refresh_backups()

    def _worker_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"{self._text('error')}: {message}")
        self.tray.notify(self._text("error"), message, error=True)
        self._show_error(message)

    def _set_busy(self, busy: bool) -> None:
        self.backup_button.setEnabled(not busy)
        self.restore_button.setEnabled(not busy)
        self.open_button.setEnabled(not busy)
        self.settings_button.setEnabled(not busy)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_() == dialog.Accepted:
            self.settings = dialog.value()
            save_settings(self.settings)
            self._retranslate_ui()
            self._apply_theme()
            self._configure_autosave()
            self._refresh_project_info()
            if self.settings.project_dir:
                self._set_project(Path(self.settings.project_dir))

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        self._allow_close = True
        self.close()

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, self._text("error"), message)

    def closeEvent(self, event) -> None:
        if self.settings.minimize_to_tray and not self._allow_close and self.tray.tray.isVisible():
            self.hide()
            self.tray.notify(self._text("title"), self._text("tray"))
            event.ignore()
            return
        if self.worker and self.worker.isRunning():
            self.worker.wait(3000)
        self.autosave_timer.stop()
        event.accept()
