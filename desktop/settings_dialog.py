"""Settings dialog for CodeSaver Desktop."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .utils import DESKTOP_THEMES, DesktopSettings


class SettingsDialog(QDialog):
    """Edit persistent desktop preferences without external dependencies."""

    def __init__(self, settings: DesktopSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings_value = settings
        russian = settings.language == "ru"
        self.setWindowTitle("Настройки CodeSaver" if russian else "CodeSaver Settings")
        self.setMinimumWidth(560)
        form = QFormLayout()

        self.excluded_dirs = QLineEdit(", ".join(settings.excluded_dirs))
        self.excluded_extensions = QLineEdit(", ".join(settings.excluded_extensions))
        self.interval = QSpinBox()
        self.interval.setRange(0, 1440)
        self.interval.setValue(settings.interval_minutes)
        self.keep_last = QSpinBox()
        self.keep_last.setRange(0, 100000)
        self.keep_last.setValue(settings.keep_last)

        self.language = QComboBox()
        self.language.addItem("Авто (язык системы)" if russian else "Auto (system language)", "auto")
        self.language.addItem("Русский", "ru")
        self.language.addItem("English", "en")
        self.language.setCurrentIndex(max(0, self.language.findData(settings.language)))

        self.theme = QComboBox()
        theme_labels = {
            "system": "Системная" if russian else "System",
            "dark": "Тёмная" if russian else "Dark",
            "light": "Светлая" if russian else "Light",
            "midnight": "Midnight",
            "ocean": "Ocean",
            "forest": "Forest",
            "high-contrast": "High contrast",
        }
        for value in DESKTOP_THEMES:
            self.theme.addItem(theme_labels[value], value)
        self.theme.setCurrentIndex(max(0, self.theme.findData(settings.theme)))

        self.accent_color = settings.accent_color
        self.accent_button = QPushButton(self.accent_color)
        self.accent_button.clicked.connect(self._choose_accent_color)
        self._update_accent_button()

        self.compress = QCheckBox("Максимальное ZIP-сжатие" if russian else "Maximum ZIP compression")
        self.compress.setChecked(settings.compress)
        self.minimize_to_tray = QCheckBox("Сворачивать в трей при закрытии" if russian else "Minimize to tray on close")
        self.minimize_to_tray.setChecked(settings.minimize_to_tray)
        self.backup_on_start = QCheckBox("Создавать бэкап при запуске" if russian else "Create a backup on startup")
        self.backup_on_start.setChecked(settings.backup_on_start)
        self.verify_after_backup = QCheckBox(
            "Проверять ZIP после бэкапа" if russian else "Verify ZIP after every backup"
        )
        self.verify_after_backup.setChecked(settings.verify_after_backup)

        backup_row = QHBoxLayout()
        self.backup_dir = QLineEdit(settings.backup_dir or "")
        browse = QPushButton("Выбрать" if russian else "Browse")
        browse.clicked.connect(self._choose_backup_dir)
        backup_row.addWidget(self.backup_dir)
        backup_row.addWidget(browse)

        form.addRow("Исключаемые папки:" if russian else "Excluded directories:", self.excluded_dirs)
        form.addRow("Исключаемые расширения:" if russian else "Excluded extensions:", self.excluded_extensions)
        form.addRow(
            "Автосохранение, минут (0 — выкл.):" if russian else "Autosave interval, minutes (0 = off):", self.interval
        )
        form.addRow("Хранить бэкапов (0 — без лимита):" if russian else "Keep backups (0 = unlimited):", self.keep_last)
        form.addRow("Язык:" if russian else "Language:", self.language)
        form.addRow("Тема:" if russian else "Theme:", self.theme)
        form.addRow("Акцентный цвет:" if russian else "Accent color:", self.accent_button)
        form.addRow("Папка бэкапов:" if russian else "Backup directory:", backup_row)
        form.addRow("", self.compress)
        form.addRow("", self.minimize_to_tray)
        form.addRow("", self.backup_on_start)
        form.addRow("", self.verify_after_backup)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Настройки применяются после OK." if russian else "Settings apply after pressing OK."))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _choose_backup_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Backup directory")
        if directory:
            self.backup_dir.setText(directory)

    def _choose_accent_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.accent_color), self, "Accent color")
        if color.isValid():
            self.accent_color = color.name().upper()
            self._update_accent_button()

    def _update_accent_button(self) -> None:
        self.accent_button.setText(self.accent_color)
        self.accent_button.setStyleSheet(
            f"background:{self.accent_color}; color:#FFFFFF; font-weight:bold; padding:6px;"
        )

    def value(self) -> DesktopSettings:
        backup_dir = self.backup_dir.text().strip()
        return DesktopSettings(
            project_dir=self.settings_value.project_dir,
            backup_dir=str(Path(backup_dir).expanduser().resolve()) if backup_dir else None,
            excluded_dirs=tuple(item.strip() for item in self.excluded_dirs.text().split(",") if item.strip()),
            excluded_extensions=tuple(
                item.strip().lower() for item in self.excluded_extensions.text().split(",") if item.strip()
            ),
            interval_minutes=self.interval.value(),
            keep_last=self.keep_last.value(),
            language=self.language.currentData(),
            theme=self.theme.currentData(),
            accent_color=self.accent_color,
            minimize_to_tray=self.minimize_to_tray.isChecked(),
            compress=self.compress.isChecked(),
            max_size=self.settings_value.max_size,
            recent_projects=self.settings_value.recent_projects,
            backup_on_start=self.backup_on_start.isChecked(),
            verify_after_backup=self.verify_after_backup.isChecked(),
        )
