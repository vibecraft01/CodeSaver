"""Main CodeSaver Desktop window."""

from __future__ import annotations

from pathlib import Path
from shutil import disk_usage

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QKeySequence
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QMenu,
    QProgressBar,
    QPushButton,
    QShortcut,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import QUrl

from codesaver.core import BackupError

from .backup_manager import DesktopBackupManager
from .settings_dialog import SettingsDialog
from .tray_icon import TrayIcon
from .utils import (
    DesktopSettings,
    archive_details,
    backup_summary,
    detect_system_language,
    detect_system_theme,
    format_bytes,
    load_settings,
    save_settings,
    theme_colors,
)

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


# Keep the UI strings in one place and use UTF-8 text for the refreshed
# controls. The original translations remain as a fallback for older keys.
TEXT["ru"].update(
    {
        "open": "Открыть папку",
        "open_backups": "Открыть папку бэкапов",
        "backup": "Создать бэкап",
        "restore": "Восстановить из бэкапа",
        "settings": "Настройки",
        "path": "Путь: {path}",
        "stats": "Файлов: {count} • Размер: {size}",
        "progress": "{current}/{total} • {processed}/{total_bytes} ({percent}%)",
        "ready": "Готово",
        "choose_project": "Сначала выберите папку проекта.",
        "backup_started": "Создание бэкапа…",
        "backup_done": "Бэкап создан",
        "restore_done": "Восстановлено файлов: {count}",
        "disk_warning": "На диске осталось мало места: {free}",
    }
)
TEXT["ru"].update(
    {
        "backup_stats": (
            "\u0411\u044d\u043a\u0430\u043f\u044b: {count} \u2022 " "\u0417\u0430\u043d\u044f\u0442\u043e: {size}"
        ),
        "copy_archive_path": (
            "\u041a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c "
            "\u043f\u0443\u0442\u044c \u0430\u0440\u0445\u0438\u0432\u0430"
        ),
        "archive_path_copied": (
            "\u041f\u0443\u0442\u044c \u0430\u0440\u0445\u0438\u0432\u0430 "
            "\u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d"
        ),
        "open_archive_folder": (
            "\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u0430\u043f\u043a\u0443 "
            "\u0430\u0440\u0445\u0438\u0432\u0430"
        ),
    }
)
TEXT["en"].update(
    {
        "open_backups": "Open backups folder",
        "path": "Path: {path}",
        "stats": "Files: {count} • Size: {size}",
        "progress": "{current}/{total} • {processed}/{total_bytes} ({percent}%)",
        "backup_started": "Creating backup…",
    }
)

_DESKTOP_1_0_2_TEXT = {
    "recent": "Recent projects",
    "cleanup": "Clean old backups",
    "cleanup_confirm": "Delete old backups according to the retention setting? This cannot be undone.",
    "cleanup_done": "Backups removed: {count}",
    "recent_empty": "No recent projects",
    "drop_project": "Drop a project folder here",
    "backup_warning": "Less than 1 GB of free disk space remains. Continue?",
    "file_warning": "Backup created, but {count} file(s) were skipped.",
    "restore_warning": "Existing project files may be overwritten. Restore this archive?",
    "operation_failed": "Backup operation failed: {error}",
}
_DESKTOP_1_0_4_TEXT = {
    "verify": "Verify backup",
    "verify_started": "Verifying backup…",
    "verify_done": "Backup verified: {count} archive entries",
    "search_archives": "Search backups…",
    "no_archive_selected": "Select a backup first.",
}
_DESKTOP_1_0_5_TEXT = {
    "refresh": "Refresh backups",
    "auto_refresh": "Backups refresh automatically every 30 seconds",
}
TEXT["en"].update(_DESKTOP_1_0_2_TEXT)
TEXT["en"].update(_DESKTOP_1_0_4_TEXT)
TEXT["en"].update(_DESKTOP_1_0_5_TEXT)
TEXT["en"].update(
    {
        "backup_stats": "Backups: {count} • Stored: {size}",
        "copy_archive_path": "Copy archive path",
        "archive_path_copied": "Archive path copied",
        "open_archive_folder": "Open archive folder",
    }
)
TEXT["ru"].update(
    {
        "recent": "\u041d\u0435\u0434\u0430\u0432\u043d\u0438\u0435 \u043f\u0440\u043e\u0435\u043a\u0442\u044b",
        "cleanup": "\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0431\u044d\u043a\u0430\u043f\u044b",
        "cleanup_confirm": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0441\u0442\u0430\u0440\u044b\u0435?",
        "cleanup_done": "\u041e\u0447\u0438\u0449\u0435\u043d\u043e: {count}",
        "recent_empty": "\u041d\u0435\u0442 \u043f\u0440\u043e\u0435\u043a\u0442\u043e\u0432",
        "drop_project": "Перетащите папку сюда",
        "backup_warning": "Меньше 1 ГБ. Продолжить?",
        "file_warning": "Пропущено файлов: {count}",
        "restore_warning": "Файлы могут быть заменены. Восстановить?",
        "operation_failed": "Ошибка операции: {error}",
    }
)
TEXT["ru"].update({"refresh": "Обновить бэкапы", "auto_refresh": "Бэкапы обновляются каждые 30 секунд"})
TEXT["ru"].update(
    {
        "verify": "Проверить бэкап",
        "verify_started": "Проверка бэкапа…",
        "verify_done": "Бэкап проверен: элементов в архиве {count}",
        "search_archives": "Поиск по бэкапам…",
        "no_archive_selected": "Сначала выберите бэкап.",
    }
)


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
            elif self.operation == "verify":
                count = self.manager.verify_backup(self.archive)
                self.succeeded.emit(str(count))
            else:
                count = self.manager.restore_backup(self.archive, overwrite=True)
                self.succeeded.emit(str(count))
        except (BackupError, OSError, ValueError) as exc:
            self.failed.emit(exc.localized(self.language) if isinstance(exc, BackupError) else str(exc))
        except Exception as exc:  # Keep unexpected filesystem/ZIP errors visible in the GUI.
            self.failed.emit(TEXT[self.language].get("operation_failed", "Operation failed").format(error=exc))

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
        self._active_language = detect_system_language() if self.settings.language == "auto" else self.settings.language
        self.setAcceptDrops(True)
        self.setMinimumSize(820, 560)
        self._build_ui()
        self._setup_tray()
        self._apply_theme()
        self._configure_autosave()
        self._configure_backup_refresh()
        if self.settings.project_dir and Path(self.settings.project_dir).is_dir():
            self._set_project(Path(self.settings.project_dir))

    def _text(self, key: str, **values: object) -> str:
        return TEXT[self._active_language].get(key, key).format(**values)

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
        self.open_backups_button = QPushButton(self._text("open_backups"))
        self.open_backups_button.clicked.connect(self._open_backup_folder)
        header.addWidget(self.open_backups_button)
        self.recent_button = QPushButton(self._text("recent"))
        self.recent_button.setMenu(QMenu(self.recent_button))
        header.addWidget(self.recent_button)
        self.refresh_button = QPushButton(self._text("refresh"))
        self.refresh_button.clicked.connect(self._refresh_backups)
        header.addWidget(self.refresh_button)
        project_layout.addLayout(header)
        self.path_label = QLabel(self._text("path", path="—"))
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.stats_label = QLabel(self._text("stats", count=0, size=format_bytes(0)))
        self.backup_stats_label = QLabel(self._text("backup_stats", count=0, size=format_bytes(0)))
        project_layout.addWidget(self.path_label)
        project_layout.addWidget(self.stats_label)
        project_layout.addWidget(self.backup_stats_label)
        layout.addWidget(project_frame)

        actions = QHBoxLayout()
        self.backup_button = QPushButton(self._text("backup"))
        self.backup_button.clicked.connect(self._start_backup)
        self.restore_button = QPushButton(self._text("restore"))
        self.restore_button.clicked.connect(self._restore_selected)
        self.verify_button = QPushButton(self._text("verify"))
        self.verify_button.clicked.connect(self._verify_selected)
        self.settings_button = QPushButton(self._text("settings"))
        self.settings_button.clicked.connect(self._open_settings)
        self.cleanup_button = QPushButton(self._text("cleanup"))
        self.cleanup_button.clicked.connect(self._cleanup_old_backups)
        actions.addWidget(self.backup_button)
        actions.addWidget(self.restore_button)
        actions.addWidget(self.verify_button)
        actions.addWidget(self.cleanup_button)
        actions.addStretch()
        actions.addWidget(self.settings_button)
        layout.addLayout(actions)

        self.archive_search = QLineEdit()
        self.archive_search.setPlaceholderText(self._text("search_archives"))
        self.archive_search.textChanged.connect(self._refresh_backups)
        layout.addWidget(self.archive_search)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([self._text("archive"), self._text("date"), self._text("size")])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self._restore_selected())
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_archive_menu)
        layout.addWidget(self.table, 1)

        self.backup_shortcut = QShortcut(QKeySequence("Ctrl+B"), self)
        self.backup_shortcut.activated.connect(self._start_backup)
        self.restore_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.restore_shortcut.activated.connect(self._restore_selected)
        self.refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        self.refresh_shortcut.activated.connect(self._refresh_backups)

        progress_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        self.progress_animation = QPropertyAnimation(self.progress, b"value", self)
        self.progress_animation.setDuration(260)
        self.progress_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.progress_text = QLabel(self._progress_text(0, 0, 0, 0))
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.progress_text)
        layout.addLayout(progress_row)
        self.setCentralWidget(central)
        self.drop_hint = QLabel(self._text("drop_project"))
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setObjectName("dropHint")
        layout.addWidget(self.drop_hint)
        self._refresh_recent_projects_menu()
        self._retranslate_ui()
        self.statusBar().showMessage(self._text("ready"))

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self._text("title"))
        self.project_header.setText(f"<b>{self._text('project')}</b>")
        self.open_button.setText(self._text("open"))
        self.open_backups_button.setText(self._text("open_backups"))
        self.recent_button.setText(self._text("recent"))
        self.refresh_button.setText(self._text("refresh"))
        self.backup_button.setText(self._text("backup"))
        self.restore_button.setText(self._text("restore"))
        self.verify_button.setText(self._text("verify"))
        self.cleanup_button.setText(self._text("cleanup"))
        self.settings_button.setText(self._text("settings"))
        self.drop_hint.setText(self._text("drop_project"))
        self.archive_search.setPlaceholderText(self._text("search_archives"))
        self.table.setHorizontalHeaderLabels([self._text("archive"), self._text("date"), self._text("size")])

    def _setup_tray(self) -> None:
        self.tray = TrayIcon(self)
        self.tray.show_requested.connect(self._show_from_tray)
        self.tray.backup_requested.connect(self._start_backup)
        self.tray.quit_requested.connect(self._quit_from_tray)
        self.tray.show()

    def _apply_theme(self) -> None:
        theme = detect_system_theme() if self.settings.theme == "system" else self.settings.theme
        colors = theme_colors(theme, self.settings.accent_color)
        stylesheet = (
            "QMainWindow,QWidget{{background:{background};color:{text};}}"
            "QFrame{{border:1px solid {border};border-radius:6px;}}"
            "QPushButton{{background:{button};color:{text};border:1px solid {border};"
            "padding:8px 14px;border-radius:5px;}}"
            "QPushButton:hover{{background:{panel};border-color:{accent};}}"
            "QTableWidget{{background:{panel};color:{text};gridline-color:{border};border:1px solid {border};}}"
            "QHeaderView::section{{background:{button};color:{text};padding:6px;border:0;}}"
            "QProgressBar{{border:1px solid {border};border-radius:4px;text-align:center;}}"
            "QProgressBar::chunk{{background:{accent};}}"
            "QLineEdit,QSpinBox,QComboBox{{background:{panel};color:{text};border:1px solid {border};padding:4px;}}"
            "QMenu{{background:{panel};color:{text};border:1px solid {border};}}"
        ).format(**colors)
        self.setStyleSheet(stylesheet)

    def _configure_autosave(self) -> None:
        if hasattr(self, "autosave_timer"):
            self.autosave_timer.stop()
        self.autosave_timer = QTimer(self)
        if self.settings.interval_minutes > 0:
            self.autosave_timer.timeout.connect(self._autosave)
            self.autosave_timer.start(self.settings.interval_minutes * 60 * 1000)
        if self.settings.backup_on_start:
            QTimer.singleShot(1200, lambda: self._start_backup_internal(automatic=True))

    def _configure_backup_refresh(self) -> None:
        if hasattr(self, "backup_refresh_timer"):
            self.backup_refresh_timer.stop()
        self.backup_refresh_timer = QTimer(self)
        self.backup_refresh_timer.timeout.connect(self._refresh_backups)
        self.backup_refresh_timer.start(30 * 1000)

    def _choose_project(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, self._text("open"))
        if directory:
            self._set_project(Path(directory))

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() and any(
            url.isLocalFile() and Path(url.toLocalFile()).is_dir() for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.is_dir():
                    self._set_project(path)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def _refresh_recent_projects_menu(self) -> None:
        menu = self.recent_button.menu()
        menu.clear()
        projects = [Path(value) for value in self.settings.recent_projects if Path(value).is_dir()]
        if not projects:
            action = menu.addAction(self._text("recent_empty"))
            action.setEnabled(False)
            return
        for project in projects[:5]:
            action = menu.addAction(str(project))
            action.triggered.connect(lambda _checked=False, path=project: self._set_project(path))

    def _remember_recent_project(self, path: Path) -> None:
        value = str(path.resolve())
        recent = [value, *self.settings.recent_projects]
        self.settings.recent_projects = tuple(dict.fromkeys(recent))[:5]

    def _set_project(self, path: Path) -> None:
        if not path.is_dir():
            self._show_error(f"{self._text('error')}: {path}")
            return
        self.settings.project_dir = str(path.resolve())
        self._remember_recent_project(path)
        self.manager = DesktopBackupManager(path, self.settings)
        self.path_label.setText(self._text("path", path=path.resolve()))
        self._refresh_project_info()
        self._refresh_backups()
        save_settings(self.settings)
        self._refresh_recent_projects_menu()
        self.statusBar().showMessage(self._text("ready"))

    def _open_backup_folder(self) -> None:
        if self.manager:
            backup_dir = self.manager.backup_dir
        elif self.settings.backup_dir:
            backup_dir = Path(self.settings.backup_dir)
        else:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(backup_dir))):
                raise OSError("Could not open the backups folder")
        except OSError as exc:
            self._show_error(str(exc))

    def _refresh_project_info(self) -> None:
        if not self.manager:
            return
        try:
            files = self.manager.list_files()
            total = sum(path.stat().st_size for path in files)
            self.stats_label.setText(self._text("stats", count=len(files), size=format_bytes(total)))
        except (BackupError, OSError) as exc:
            self._show_error(str(exc))

    def _refresh_backups(self, _query: str = "") -> None:
        self.table.setRowCount(0)
        if not self.manager:
            self.backup_stats_label.setText(self._text("backup_stats", count=0, size=format_bytes(0)))
            return
        try:
            query = self.archive_search.text().strip().lower()
            all_archives = archive_details(self.manager.backup_dir)
            count, total_size = backup_summary(self.manager.backup_dir)
            self.backup_stats_label.setText(self._text("backup_stats", count=count, size=format_bytes(total_size)))
            archives = all_archives
            archives = [item for item in archives if not query or query in item[0].name.lower()]
            for row, (path, date, size) in enumerate(archives):
                self.table.insertRow(row)
                item = QTableWidgetItem(path.name)
                item.setData(Qt.UserRole, str(path))
                self.table.setItem(row, 0, item)
                self.table.setItem(row, 1, QTableWidgetItem(date))
                self.table.setItem(row, 2, QTableWidgetItem(size))
        except OSError as exc:
            self._show_error(str(exc))

    def _show_archive_menu(self, position) -> None:
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        self.table.selectRow(row)
        archive = Path(self.table.item(row, 0).data(Qt.UserRole))
        menu = QMenu(self)
        copy_action = menu.addAction(self._text("copy_archive_path"))
        open_action = menu.addAction(self._text("open_archive_folder"))
        selected = menu.exec_(self.table.viewport().mapToGlobal(position))
        if selected == copy_action:
            QApplication.clipboard().setText(str(archive))
            self.statusBar().showMessage(self._text("archive_path_copied"))
        elif selected == open_action:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(archive.parent)))

    def _progress_text(self, current: int, total: int, processed: int, total_bytes: int) -> str:
        percent = 0 if total == 0 else int(current / total * 100)
        return self._text(
            "progress",
            current=current,
            total=total,
            processed=format_bytes(processed),
            total_bytes=format_bytes(total_bytes),
            percent=percent,
        )

    def _animate_progress(self, percent: int) -> None:
        current = self.progress.value()
        self.progress_animation.stop()
        self.progress_animation.setStartValue(current)
        self.progress_animation.setEndValue(max(0, min(100, percent)))
        self.progress_animation.start()

    def _start_backup(self) -> None:
        self._start_backup_internal(automatic=False)

    def _start_backup_internal(self, automatic: bool) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        if self.worker and self.worker.isRunning():
            return
        if not self._has_enough_disk_space(automatic):
            return
        self._operation = "backup"
        self.progress.setValue(0)
        self.progress_text.setText(self._progress_text(0, 0, 0, 0))
        self._animate_progress(0)
        self.statusBar().showMessage(self._text("backup_started"))
        self._set_busy(True)
        self.worker = BackupWorker(self.manager, "backup", language=self._active_language)
        self._connect_worker()
        self.worker.start()

    def _autosave(self) -> None:
        if self.manager and not (self.worker and self.worker.isRunning()):
            self._start_backup_internal(automatic=True)

    def _has_enough_disk_space(self, automatic: bool) -> bool:
        if not self.manager:
            return False
        location = self.manager.backup_dir if self.manager.backup_dir.exists() else self.manager.backup_dir.parent
        try:
            free = disk_usage(location).free
        except OSError as exc:
            self._show_error(f"{self._text('error')}: {exc}")
            return False
        if free >= 1024**3:
            return True
        self.tray.notify(self._text("error"), self._text("disk_warning", free=format_bytes(free)), error=True)
        if automatic:
            return True
        return (
            QMessageBox.warning(
                self,
                self._text("error"),
                self._text("backup_warning"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            == QMessageBox.Yes
        )

    def _restore_selected(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        row = self.table.currentRow()
        if row < 0:
            return
        archive = Path(self.table.item(row, 0).data(Qt.UserRole))
        answer = QMessageBox.warning(
            self,
            self._text("confirm"),
            self._text("confirm_restore") + "\n\n" + self._text("restore_warning"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._operation = "restore"
        self.statusBar().showMessage(self._text("backup_started"))
        self._set_busy(True)
        self.worker = BackupWorker(self.manager, "restore", archive, language=self._active_language)
        self._connect_worker()
        self.worker.start()

    def _verify_selected(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        row = self.table.currentRow()
        if row < 0:
            self.statusBar().showMessage(self._text("no_archive_selected"))
            return
        archive = Path(self.table.item(row, 0).data(Qt.UserRole))
        self._operation = "verify"
        self.statusBar().showMessage(self._text("verify_started"))
        self._set_busy(True)
        self.worker = BackupWorker(self.manager, "verify", archive, language=self._active_language)
        self._connect_worker()
        self.worker.start()

    def _connect_worker(self) -> None:
        self.worker.progress.connect(self._update_progress)
        self.worker.succeeded.connect(self._worker_succeeded)
        self.worker.failed.connect(self._worker_failed)
        self.worker.finished.connect(lambda: self._set_busy(False))

    def _update_progress(self, current: int, total: int, processed: int, total_bytes: int) -> None:
        percent = 100 if total == 0 else int(current / total * 100)
        self._animate_progress(percent)
        self.progress_text.setText(self._progress_text(current, total, processed, total_bytes))
        self.tray.set_progress(percent)

    def _worker_succeeded(self, value: str) -> None:
        if self._operation == "backup":
            self._animate_progress(100)
            self.tray.set_progress(100)
            self.statusBar().showMessage(self._text("backup_done"))
            self.tray.notify(self._text("title"), self._text("backup_done"))
            if self.manager and self.manager.last_errors:
                self.tray.notify(
                    self._text("error"),
                    self._text("file_warning", count=len(self.manager.last_errors)),
                    error=True,
                )
            if self.manager:
                free_space = disk_usage(self.manager.backup_dir).free
                if free_space < 100 * 1024 * 1024:
                    self.tray.notify(
                        self._text("error"), self._text("disk_warning", free=format_bytes(free_space)), error=True
                    )
        elif self._operation == "verify":
            self.statusBar().showMessage(self._text("verify_done", count=value))
            self.tray.notify(self._text("title"), self._text("verify_done", count=value))
        else:
            self.statusBar().showMessage(self._text("restore_done", count=value))
        self._refresh_project_info()
        self._refresh_backups()

    def _worker_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"{self._text('error')}: {message}")
        self.tray.notify(self._text("error"), message, error=True)
        self.tray.set_progress(None)
        self._show_error(message)

    def _set_busy(self, busy: bool) -> None:
        self.backup_button.setEnabled(not busy)
        self.restore_button.setEnabled(not busy)
        self.verify_button.setEnabled(not busy)
        self.open_button.setEnabled(not busy)
        self.open_backups_button.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        self.settings_button.setEnabled(not busy)
        self.cleanup_button.setEnabled(not busy)

    def _cleanup_old_backups(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        answer = QMessageBox.warning(
            self,
            self._text("confirm"),
            self._text("cleanup_confirm"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            count = self.manager.cleanup_old_backups()
            self.statusBar().showMessage(self._text("cleanup_done", count=count))
            self._refresh_backups()
        except (BackupError, OSError, ValueError) as exc:
            self._show_error(str(exc))

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_() == dialog.Accepted:
            self.settings = dialog.value()
            self._active_language = (
                detect_system_language() if self.settings.language == "auto" else self.settings.language
            )
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
        self.backup_refresh_timer.stop()
        event.accept()
