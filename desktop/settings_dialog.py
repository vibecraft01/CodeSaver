"""Settings dialog for CodeSaver Desktop."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtWidgets import (
    QCheckBox,
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

from .utils import DesktopSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: DesktopSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings_value = settings
        self.setWindowTitle("Настройки CodeSaver" if settings.language == "ru" else "CodeSaver Settings")
        self.setMinimumWidth(520)
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
        self.language.addItem("Русский", "ru")
        self.language.addItem("English", "en")
        self.language.setCurrentIndex(0 if settings.language == "ru" else 1)
        self.theme = QComboBox()
        self.theme.addItem("Тёмная" if settings.language == "ru" else "Dark", "dark")
        self.theme.addItem("Светлая" if settings.language == "ru" else "Light", "light")
        self.theme.setCurrentIndex(0 if settings.theme == "dark" else 1)
        self.compress = QCheckBox("Максимальное ZIP-сжатие" if settings.language == "ru" else "Maximum ZIP compression")
        self.compress.setChecked(settings.compress)
        self.minimize_to_tray = QCheckBox(
            "Сворачивать в трей при закрытии" if settings.language == "ru" else "Minimize to tray on close"
        )
        self.minimize_to_tray.setChecked(settings.minimize_to_tray)

        backup_row = QHBoxLayout()
        self.backup_dir = QLineEdit(settings.backup_dir or "")
        browse = QPushButton("Выбрать" if settings.language == "ru" else "Browse")
        browse.clicked.connect(self._choose_backup_dir)
        backup_row.addWidget(self.backup_dir)
        backup_row.addWidget(browse)

        form.addRow("Исключаемые папки:" if settings.language == "ru" else "Excluded directories:", self.excluded_dirs)
        form.addRow(
            "Исключаемые расширения:" if settings.language == "ru" else "Excluded extensions:", self.excluded_extensions
        )
        form.addRow(
            (
                "Автосохранение, минут (0 — выкл.):"
                if settings.language == "ru"
                else "Autosave interval, minutes (0 = off):"
            ),
            self.interval,
        )
        form.addRow(
            "Хранить бэкапов (0 — без лимита):" if settings.language == "ru" else "Keep backups (0 = unlimited):",
            self.keep_last,
        )
        form.addRow("Язык:" if settings.language == "ru" else "Language:", self.language)
        form.addRow("Тема:" if settings.language == "ru" else "Theme:", self.theme)
        form.addRow("Папка бэкапов:" if settings.language == "ru" else "Backup directory:", backup_row)
        form.addRow("", self.compress)
        form.addRow("", self.minimize_to_tray)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Настройки применяются после нажатия OK."
                if settings.language == "ru"
                else "Settings apply after pressing OK."
            )
        )
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _choose_backup_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Папка бэкапов")
        if directory:
            self.backup_dir.setText(directory)

    def value(self) -> DesktopSettings:
        language = self.language.currentData()
        return DesktopSettings(
            project_dir=self.settings_value.project_dir,
            backup_dir=(
                str(Path(self.backup_dir.text()).expanduser().resolve()) if self.backup_dir.text().strip() else None
            ),
            excluded_dirs=tuple(item.strip() for item in self.excluded_dirs.text().split(",") if item.strip()),
            excluded_extensions=tuple(
                item.strip().lower() for item in self.excluded_extensions.text().split(",") if item.strip()
            ),
            interval_minutes=self.interval.value(),
            keep_last=self.keep_last.value(),
            language=language,
            theme=self.theme.currentData(),
            minimize_to_tray=self.minimize_to_tray.isChecked(),
            compress=self.compress.isChecked(),
            max_size=self.settings_value.max_size,
        )
