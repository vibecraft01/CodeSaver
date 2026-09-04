"""Main CodeSaver Desktop window."""

from __future__ import annotations

import json
import hashlib
import platform
import subprocess
import csv
from collections import Counter
from pathlib import Path
from shutil import disk_usage
import time
import zipfile

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
    QInputDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import QUrl

from codesaver.core import BackupError
from codesaver.cloud import upload_archive

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
    git_context,
    export_backup_report,
    export_compare_report,
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
        "verify_all": "Проверить все бэкапы",
        "verify_all_started": "Проверка всех бэкапов…",
        "verify_all_done": "Состояние бэкапов: {verified}/{total} проверено",
        "autosave_status": "Автосохранение: {status}",
        "autosave_off": "\u0432\u044b\043a\u043b\044e\0447\u0435\u043d\u043e",
        "autosave_next": "every {minutes} min • next in {remaining}",
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
    "restore_safety": "A safety backup of the current project will be created first.",
    "export_compare": "Export comparison JSON",
    "export_compare_done": "Comparison report exported: {path}",
    "git_status": "Git: {branch} • {commit} • {dirty}",
    "git_not_repo": "Git: not a repository",
    "recent": "Recent projects",
    "cleanup": "Clean old backups",
    "cleanup_confirm": "Delete old backups according to the retention setting? This cannot be undone.",
    "cleanup_done": "Backups removed: {count}",
    "export_report": "Export JSON report",
    "export_report_done": "Report exported: {path}",
    "restore_files": "Restore selected files",
    "restore_files_prompt": "Enter the archive paths to restore, one per line:",
    "restore_files_done": "Selected files restored: {count}",
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
_DESKTOP_1_0_7_TEXT = {
    "verify_all": "Verify all backups",
    "verify_all_started": "Verifying all backups…",
    "verify_all_done": "Backup health: {verified}/{total} verified",
    "autosave_status": "Autosave: {status}",
    "autosave_off": "off",
    "autosave_next": "every {minutes} min • next in {remaining}",
}
_DESKTOP_1_0_9_TEXT = {
    "compare": "Compare",
    "compare_started": "Comparing project with backup…",
    "compare_title": "Backup comparison",
    "compare_summary": "Added: {added}\nModified: {modified}\nMissing: {missing}",
    "compare_details": "Added files:\n{added}\n\nModified files:\n{modified}\n\nMissing files:\n{missing}",
}
_DESKTOP_1_1_5_TEXT = {
    "archive_info": "Archive details",
    "archive_info_body": "Name: {name}\nCreated: {date}\nSize: {size}\nFiles: {files}\nPath: {path}",
    "export_manifest": "Export archive manifest",
    "export_manifest_done": "Manifest exported: {path}",
    "rename_archive": "Rename archive",
    "rename_prompt": "New archive name:",
    "rename_done": "Archive renamed",
    "delete_archive": "Delete archive",
    "delete_confirm": "Permanently delete {name}?",
    "delete_done": "Archive deleted",
    "open_project_folder": "Open project folder",
}
_DESKTOP_1_1_6_TEXT = {
    "sha256": "SHA-256: {checksum}",
    "search_results": "Showing {shown} of {total} backups",
    "focus_search": "Focus backup search",
}
_DESKTOP_1_1_7_TEXT = {
    "copy_project_path": "Copy project path",
    "project_path_copied": "Project path copied",
    "open_terminal": "Open terminal here",
    "terminal_failed": "Could not open terminal: {error}",
    "copy_checksum": "Copy SHA-256",
    "checksum_copied": "SHA-256 copied",
    "clear_search": "Clear backup search",
}
_DESKTOP_1_1_8_TEXT = {
    "shortcut_help": (
        "Shortcuts: Ctrl+B backup • Ctrl+R restore • Ctrl+D compare • "
        "Ctrl+Shift+V verify • Ctrl+F search • Ctrl+L clear search • Ctrl+Shift+T terminal"
    ),
}
_DESKTOP_1_1_9_TEXT = {
    "developer_dashboard": "Developer dashboard",
    "developer_dashboard_body": (
        "Files: {files}\nProject size: {size}\nExtensions: {extensions}\n"
        "Largest file: {largest}\nGit branch: {branch}\nCommit: {commit}\n"
        "Working tree: {dirty}\nBackups: {backups}"
    ),
}
_DESKTOP_1_2_0_TEXT = {
    "project_audit": "Project audit",
    "export_dashboard": "Export dashboard JSON",
    "dashboard_exported": "Dashboard exported: {path}",
    "copy_dashboard": "Copy dashboard summary",
    "dashboard_copied": "Dashboard copied",
    "open_git_changes": "Open Git changes",
    "refresh_project": "Refresh project analysis",
    "autosave_pause": "Pause autosave",
    "autosave_resume": "Resume autosave",
}
_DESKTOP_1_2_1_TEXT = {
    "project_tools": "Project tools",
    "export_inventory": "Export file inventory CSV",
    "inventory_exported": "File inventory exported: {path}",
    "show_exclusions": "Show exclusion rules",
    "exclusions_body": "Directories: {directories}\nExtensions: {extensions}",
    "symlinks": "Find symbolic links",
    "symlinks_body": "Symbolic links ({count}):\n{items}",
    "copy_git_context": "Copy Git context",
    "git_context_copied": "Git context copied",
    "open_config": "Open Desktop configuration",
    "export_tree": "Export project tree JSON",
    "tree_exported": "Project tree exported: {path}",
    "copy_backup_command": "Copy backup command",
    "backup_command_copied": "Backup command copied",
    "largest_project_files": "Show largest project files",
    "unreadable_project_files": "Find unreadable project files",
    "project_check": "Run project health check",
    "project_check_body": "Files: {files}\nUnreadable: {unreadable}\nTotal size: {size}",
    "duplicates": "Find duplicate files",
    "integrity_report": "Export archive integrity report",
    "integrity_done": "Integrity report exported: {path}",
    "free_space": "Show backup free space",
    "free_space_body": "Free: {free}\nTotal: {total}\nBackup folder: {path}",
    "copy_restore_command": "Copy restore command",
    "restore_command_copied": "Restore command copied",
    "search_archive_files": "Search files in selected archive",
    "search_archive_prompt": "File name or path contains:",
    "compare_archives": "Compare two archives",
    "compare_archives_prompt": "Select the second archive",
    "compare_archives_body": "Added: {added}\nRemoved: {removed}\nChanged: {changed}",
    "export_archive_hashes": "Export archive file hashes CSV",
    "archive_hashes_done": "Archive hashes exported: {path}",
    "unpacked_size": "Show unpacked archive size",
    "unpacked_size_body": "Archive: {name}\nFiles: {files}\nUnpacked size: {size}",
    "retention_preview": "Preview retention cleanup",
    "retention_body": "Archives kept: {kept}\nArchives eligible for cleanup: {remove}",
    "copy_manifest": "Copy archive manifest JSON",
    "manifest_copied": "Archive manifest copied",
    "file_types": "Show files by type",
    "stale_files": "Find stale files",
    "archive_total": "Show total archive storage",
    "git_tags": "Show Git tags",
    "backup_index": "Copy backup index JSON",
    "export_file_types": "Export file types CSV",
    "archive_timeline": "Show backup timeline",
    "empty_files": "Find empty files",
    "copy_hash_inventory": "Copy SHA-256 inventory",
    "git_remotes": "Show Git remotes",
    "archive_ratio": "Show archive compression ratio",
    "export_timeline": "Export backup timeline CSV",
    "copy_file_list": "Copy project file list",
    "archive_dates": "Show archive file dates",
    "copy_project_info": "Copy project information",
    "recent_project_files": "Show recently modified files",
    "export_archive_files": "Export archive members CSV",
    "archive_project_size": "Compare archive and project size",
    "archive_age": "Show selected archive age",
    "copy_project_files_json": "Copy project file inventory JSON",
    "archive_extensions": "Show archive extensions",
    "export_project_sizes": "Export project sizes CSV",
    "copy_backup_summary": "Copy backup summary JSON",
    "archive_duplicates": "Find duplicate archive members",
    "copy_restore_preview": "Copy restore preview",
    "archive_health_csv": "Export archive health CSV",
    "project_dirs": "Show project directories",
    "git_log_copy": "Copy Git commit history",
    "archive_ratio_csv": "Export compression report CSV",
    "backup_age_map": "Show backup age map",
    "cloud_upload": "Upload archive to cloud",
    "cloud_url": "Cloud endpoint URL",
    "cloud_uploaded": "Archive uploaded to cloud (HTTP {status})",
}
TEXT["en"].update(_DESKTOP_1_0_2_TEXT)
TEXT["en"].update(_DESKTOP_1_0_4_TEXT)
TEXT["en"].update(_DESKTOP_1_0_5_TEXT)
TEXT["en"].update(_DESKTOP_1_0_7_TEXT)
TEXT["en"].update(_DESKTOP_1_0_9_TEXT)
TEXT["en"].update(_DESKTOP_1_1_5_TEXT)
TEXT["en"].update(_DESKTOP_1_1_6_TEXT)
TEXT["en"].update(_DESKTOP_1_1_7_TEXT)
TEXT["en"].update(_DESKTOP_1_1_8_TEXT)
TEXT["en"].update(_DESKTOP_1_1_9_TEXT)
TEXT["en"].update(_DESKTOP_1_2_0_TEXT)
TEXT["en"].update(_DESKTOP_1_2_1_TEXT)
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
TEXT["ru"].update(
    {
        "project_tools": "Инструменты проекта",
        "export_inventory": "Экспортировать CSV инвентаря",
        "inventory_exported": "Инвентарь экспортирован: {path}",
        "show_exclusions": "Показать правила исключений",
        "exclusions_body": "Папки: {directories}\nРасширения: {extensions}",
        "symlinks": "Найти симлинки",
        "symlinks_body": "Симлинки ({count}):\n{items}",
        "copy_git_context": "Копировать Git-контекст",
        "git_context_copied": "Git-контекст скопирован",
        "open_config": "Открыть конфигурацию Desktop",
        "export_tree": "Экспортировать дерево проекта JSON",
        "tree_exported": "Дерево проекта экспортировано: {path}",
        "copy_backup_command": "Копировать команду backup",
        "backup_command_copied": "Команда backup скопирована",
        "largest_project_files": "Показать самые большие файлы",
        "unreadable_project_files": "Найти нечитаемые файлы",
        "project_check": "Проверить состояние проекта",
        "project_check_body": "Файлов: {files}\nНечитаемых: {unreadable}\nОбщий размер: {size}",
        "duplicates": "Найти дубликаты файлов",
        "integrity_report": "Экспортировать отчёт целостности архивов",
        "integrity_done": "Отчёт целостности экспортирован: {path}",
        "free_space": "Показать свободное место backup",
        "free_space_body": "Свободно: {free}\nВсего: {total}\nПапка backup: {path}",
        "copy_restore_command": "Копировать команду восстановления",
        "restore_command_copied": "Команда восстановления скопирована",
        "search_archive_files": "Искать файлы в выбранном архиве",
        "search_archive_prompt": "Часть имени или пути файла:",
        "compare_archives": "Сравнить два архива",
        "compare_archives_prompt": "Выберите второй архив",
        "compare_archives_body": "Добавлено: {added}\nУдалено: {removed}\nИзменено: {changed}",
        "export_archive_hashes": "Экспортировать хэши файлов архива CSV",
        "archive_hashes_done": "Хэши архива экспортированы: {path}",
        "unpacked_size": "Показать распакованный размер",
        "unpacked_size_body": "Архив: {name}\nФайлов: {files}\nРаспакованный размер: {size}",
        "retention_preview": "Предпросмотр очистки retention",
        "retention_body": "Останется: {kept}\nК очистке: {remove}",
        "copy_manifest": "Копировать JSON-манифест архива",
        "manifest_copied": "Манифест архива скопирован",
        "file_types": "Показать файлы по типам",
        "stale_files": "Найти давно изменённые файлы",
        "archive_total": "Показать общий размер архивов",
        "git_tags": "Показать Git-теги",
        "backup_index": "Копировать индекс бэкапов JSON",
        "export_file_types": "Экспортировать типы файлов CSV",
        "archive_timeline": "Показать историю бэкапов",
        "empty_files": "Найти пустые файлы",
        "copy_hash_inventory": "Копировать SHA-256 инвентаризацию",
        "git_remotes": "Показать Git remote",
        "archive_ratio": "Показать степень сжатия архива",
        "export_timeline": "Экспортировать историю бэкапов CSV",
        "copy_file_list": "Копировать список файлов проекта",
        "archive_dates": "Показать даты файлов архива",
        "copy_project_info": "Копировать сведения о проекте",
        "recent_project_files": "Показать недавно изменённые файлы",
        "export_archive_files": "Экспортировать файлы архива CSV",
        "archive_project_size": "Сравнить размер архива и проекта",
        "archive_age": "Показать возраст выбранного архива",
        "copy_project_files_json": "Копировать JSON-инвентаризацию проекта",
        "archive_extensions": "Показать расширения архива",
        "export_project_sizes": "Экспортировать размеры проекта CSV",
        "copy_backup_summary": "Копировать сводку бэкапов JSON",
        "archive_duplicates": "Найти дубликаты файлов в архиве",
        "copy_restore_preview": "Копировать предпросмотр восстановления",
        "archive_health_csv": "Экспортировать здоровье архивов CSV",
        "project_dirs": "Показать папки проекта",
        "git_log_copy": "Копировать историю коммитов Git",
        "archive_ratio_csv": "Экспортировать отчёт сжатия CSV",
        "backup_age_map": "Показать возраст бэкапов",
        "cloud_upload": "Загрузить архив в облако",
        "cloud_url": "URL облачного endpoint",
        "cloud_uploaded": "Архив загружен в облако (HTTP {status})",
    }
)
TEXT["ru"].update(
    {
        "project_audit": "Аудит проекта",
        "export_dashboard": "Экспортировать JSON панели",
        "dashboard_exported": "Панель экспортирована: {path}",
        "copy_dashboard": "Копировать сводку панели",
        "dashboard_copied": "Сводка скопирована",
        "open_git_changes": "Открыть изменения Git",
        "refresh_project": "Обновить анализ проекта",
        "autosave_pause": "Поставить автосохранение на паузу",
        "autosave_resume": "Возобновить автосохранение",
    }
)
TEXT["ru"].update(
    {
        "developer_dashboard": "Панель разработчика",
        "developer_dashboard_body": (
            "Файлов: {files}\nРазмер проекта: {size}\nРасширения: {extensions}\n"
            "Самый большой файл: {largest}\nGit-ветка: {branch}\nКоммит: {commit}\n"
            "Рабочее дерево: {dirty}\nБэкапов: {backups}"
        ),
    }
)
TEXT["ru"].update(
    {
        "shortcut_help": (
            "Клавиши: Ctrl+B бэкап • Ctrl+R восстановить • Ctrl+D сравнить • "
            "Ctrl+Shift+V проверить • Ctrl+F поиск • Ctrl+L очистить • Ctrl+Shift+T терминал"
        ),
    }
)
TEXT["ru"].update(
    {
        "copy_project_path": "Копировать путь проекта",
        "project_path_copied": "Путь проекта скопирован",
        "open_terminal": "Открыть терминал здесь",
        "terminal_failed": "Не удалось открыть терминал: {error}",
        "copy_checksum": "Копировать SHA-256",
        "checksum_copied": "SHA-256 скопирован",
        "clear_search": "Очистить поиск бэкапов",
    }
)
TEXT["ru"].update(
    {
        "sha256": "SHA-256: {checksum}",
        "search_results": "Показано бэкапов: {shown} из {total}",
        "focus_search": "Фокус на поиске бэкапов",
    }
)
TEXT["ru"].update(
    {
        "archive_info": "Сведения об архиве",
        "archive_info_body": "Имя: {name}\nСоздан: {date}\nРазмер: {size}\nФайлов: {files}\nПуть: {path}",
        "export_manifest": "Экспортировать manifest",
        "export_manifest_done": "Manifest сохранён: {path}",
        "rename_archive": "Переименовать архив",
        "rename_prompt": "Новое имя архива:",
        "rename_done": "Архив переименован",
        "delete_archive": "Удалить архив",
        "delete_confirm": "Удалить {name} навсегда?",
        "delete_done": "Архив удалён",
        "open_project_folder": "Открыть папку проекта",
    }
)
TEXT["ru"].update({"refresh": "Обновить бэкапы", "auto_refresh": "Бэкапы обновляются каждые 30 секунд"})
TEXT["ru"].update({"export_report": "Экспорт JSON-отчёта", "export_report_done": "Отчёт сохранён: {path}"})
TEXT["ru"].update({"restore_safety": "Перед восстановлением будет создан аварийный бэкап текущего проекта."})
TEXT["ru"].update(
    {
        "export_compare": "Экспорт JSON-сравнения",
        "export_compare_done": "Отчёт сравнения сохранён: {path}",
        "git_status": "Git: {branch} • {commit} • {dirty}",
        "git_not_repo": "Git: это не Git-репозиторий",
        "restore_files": "Восстановить выбранные файлы",
        "restore_files_prompt": "Укажите пути файлов из архива, по одному в строке:",
        "restore_files_done": "Выбранных файлов восстановлено: {count}",
    }
)
TEXT["ru"].update(
    {
        "verify": "Проверить бэкап",
        "verify_started": "Проверка бэкапа…",
        "verify_done": "Бэкап проверен: элементов в архиве {count}",
        "search_archives": "Поиск по бэкапам…",
        "no_archive_selected": "Сначала выберите бэкап.",
    }
)


TEXT["ru"].update(
    {
        "compare": "Сравнить",
        "compare_started": "Сравнение проекта с бэкапом…",
        "compare_title": "Сравнение бэкапа",
        "compare_summary": "Добавлено: {added}\nИзменено: {modified}\nОтсутствует: {missing}",
        "compare_details": (
            "Добавленные файлы:\n{added}\n\n" "Изменённые файлы:\n{modified}\n\n" "Отсутствующие файлы:\n{missing}"
        ),
    }
)


class BackupWorker(QThread):
    progress = pyqtSignal(int, int, int, int)
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        manager: DesktopBackupManager,
        operation: str,
        archive: Path | None = None,
        language: str = "en",
        archives: list[Path] | None = None,
    ) -> None:
        super().__init__()
        self.manager = manager
        self.operation = operation
        self.archive = archive
        self.language = language
        self.archives = archives or []

    def run(self) -> None:
        try:
            if self.operation == "backup":
                archive = self.manager.create_backup(self._progress)
                if self.manager.verify_after_backup:
                    self.manager.verify_backup(archive)
                self.succeeded.emit(str(archive))
            elif self.operation == "verify":
                count = self.manager.verify_backup(self.archive)
                self.succeeded.emit(str(count))
            elif self.operation == "verify_all":
                verified = 0
                for current, archive in enumerate(self.archives, start=1):
                    try:
                        self.manager.verify_backup(archive)
                        verified += 1
                    except (BackupError, OSError, ValueError):
                        pass
                    finally:
                        self.progress.emit(current, len(self.archives), archive, current, len(self.archives))
                self.succeeded.emit(f"{verified}/{len(self.archives)}")
            elif self.operation == "compare":
                result = self.manager.compare_backup(self.archive)
                self.succeeded.emit(json.dumps(result, ensure_ascii=False))
            else:
                safety_archive = self.manager.create_backup()
                count = self.manager.restore_backup(self.archive, overwrite=True)
                self.safety_archive = safety_archive
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
        # _retranslate_ui() runs while _build_ui() is assembling widgets, so
        # this state must exist before the autosave controls are rendered.
        self.next_autosave_at: float | None = None
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
        self.autosave_status_label = QLabel()
        self.git_status_label = QLabel()
        project_layout.addWidget(self.path_label)
        project_layout.addWidget(self.stats_label)
        project_layout.addWidget(self.backup_stats_label)
        project_layout.addWidget(self.autosave_status_label)
        project_layout.addWidget(self.git_status_label)
        layout.addWidget(project_frame)

        actions = QHBoxLayout()
        self.backup_button = QPushButton(self._text("backup"))
        self.backup_button.clicked.connect(self._start_backup)
        self.restore_button = QPushButton(self._text("restore"))
        self.restore_button.clicked.connect(self._restore_selected)
        self.verify_button = QPushButton(self._text("verify"))
        self.verify_button.clicked.connect(self._verify_selected)
        self.verify_all_button = QPushButton(self._text("verify_all"))
        self.verify_all_button.clicked.connect(self._verify_all)
        self.compare_button = QPushButton(self._text("compare"))
        self.compare_button.clicked.connect(self._compare_selected)
        self.export_compare_button = QPushButton(self._text("export_compare"))
        self.export_compare_button.clicked.connect(self._export_compare_selected)
        self.settings_button = QPushButton(self._text("settings"))
        self.settings_button.clicked.connect(self._open_settings)
        self.developer_button = QPushButton(self._text("developer_dashboard"))
        self.developer_button.clicked.connect(self._show_developer_dashboard)
        self.audit_button = QPushButton(self._text("project_audit"))
        self.audit_button.clicked.connect(self._show_developer_dashboard)
        self.export_dashboard_button = QPushButton(self._text("export_dashboard"))
        self.export_dashboard_button.clicked.connect(self._export_dashboard)
        self.copy_dashboard_button = QPushButton(self._text("copy_dashboard"))
        self.copy_dashboard_button.clicked.connect(self._copy_dashboard)
        self.git_changes_button = QPushButton(self._text("open_git_changes"))
        self.git_changes_button.clicked.connect(self._open_git_changes)
        self.refresh_project_button = QPushButton(self._text("refresh_project"))
        self.refresh_project_button.clicked.connect(self._refresh_project_info)
        self.autosave_pause_button = QPushButton(self._text("autosave_pause"))
        self.autosave_pause_button.clicked.connect(self._toggle_autosave_pause)
        self.project_tools_button = QPushButton(self._text("project_tools"))
        tools_menu = QMenu(self.project_tools_button)
        tools_menu.addAction(self._text("export_inventory"), self._export_file_inventory)
        tools_menu.addAction(self._text("show_exclusions"), self._show_exclusions)
        tools_menu.addAction(self._text("symlinks"), self._show_symlinks)
        tools_menu.addAction(self._text("copy_git_context"), self._copy_git_context)
        tools_menu.addAction(self._text("open_config"), self._open_desktop_config)
        tools_menu.addAction(self._text("cloud_upload"), self._upload_selected_to_cloud)
        tools_menu.addAction(self._text("export_tree"), self._export_project_tree)
        tools_menu.addAction(self._text("copy_backup_command"), self._copy_backup_command)
        tools_menu.addAction(self._text("largest_project_files"), self._show_largest_project_files)
        tools_menu.addAction(self._text("unreadable_project_files"), self._show_unreadable_project_files)
        tools_menu.addAction(self._text("project_check"), self._show_project_check)
        tools_menu.addAction(self._text("duplicates"), self._find_duplicate_files)
        tools_menu.addAction(self._text("integrity_report"), self._export_integrity_report)
        tools_menu.addAction(self._text("free_space"), self._show_backup_free_space)
        tools_menu.addAction(self._text("copy_restore_command"), self._copy_restore_command)
        tools_menu.addAction(self._text("search_archive_files"), self._search_selected_archive_files)
        tools_menu.addAction(self._text("compare_archives"), self._compare_two_archives)
        tools_menu.addAction(self._text("export_archive_hashes"), self._export_archive_hashes)
        tools_menu.addAction(self._text("unpacked_size"), self._show_unpacked_size)
        tools_menu.addAction(self._text("retention_preview"), self._show_retention_preview)
        tools_menu.addAction(self._text("copy_manifest"), self._copy_archive_manifest)
        tools_menu.addAction(self._text("file_types"), self._show_file_types)
        tools_menu.addAction(self._text("stale_files"), self._show_stale_files)
        tools_menu.addAction(self._text("archive_total"), self._show_archive_total)
        tools_menu.addAction(self._text("git_tags"), self._show_git_tags)
        tools_menu.addAction(self._text("backup_index"), self._copy_backup_index)
        tools_menu.addAction(self._text("export_file_types"), self._export_file_types)
        tools_menu.addAction(self._text("archive_timeline"), self._show_archive_timeline)
        tools_menu.addAction(self._text("empty_files"), self._show_empty_files)
        tools_menu.addAction(self._text("copy_hash_inventory"), self._copy_hash_inventory)
        tools_menu.addAction(self._text("git_remotes"), self._show_git_remotes)
        tools_menu.addAction(self._text("archive_ratio"), self._show_archive_ratio)
        tools_menu.addAction(self._text("export_timeline"), self._export_timeline)
        tools_menu.addAction(self._text("copy_file_list"), self._copy_file_list)
        tools_menu.addAction(self._text("archive_dates"), self._show_archive_dates)
        tools_menu.addAction(self._text("copy_project_info"), self._copy_project_info)
        tools_menu.addAction(self._text("recent_project_files"), self._show_recent_project_files)
        tools_menu.addAction(self._text("export_archive_files"), self._export_archive_files)
        tools_menu.addAction(self._text("archive_project_size"), self._compare_archive_project_size)
        tools_menu.addAction(self._text("archive_age"), self._show_archive_age)
        tools_menu.addAction(self._text("copy_project_files_json"), self._copy_project_files_json)
        tools_menu.addAction(self._text("archive_extensions"), self._show_archive_extensions)
        tools_menu.addAction(self._text("export_project_sizes"), self._export_project_sizes)
        tools_menu.addAction(self._text("copy_backup_summary"), self._copy_backup_summary)
        tools_menu.addAction(self._text("archive_duplicates"), self._find_archive_duplicates)
        tools_menu.addAction(self._text("copy_restore_preview"), self._copy_restore_preview)
        tools_menu.addAction(self._text("archive_health_csv"), self._export_archive_health_csv)
        tools_menu.addAction(self._text("project_dirs"), self._show_project_dirs)
        tools_menu.addAction(self._text("git_log_copy"), self._copy_git_log)
        tools_menu.addAction(self._text("archive_ratio_csv"), self._export_archive_ratio_csv)
        tools_menu.addAction(self._text("backup_age_map"), self._show_backup_age_map)
        self.project_tools_button.setMenu(tools_menu)
        self.cleanup_button = QPushButton(self._text("cleanup"))
        self.cleanup_button.clicked.connect(self._cleanup_old_backups)
        self.export_report_button = QPushButton(self._text("export_report"))
        self.export_report_button.clicked.connect(self._export_report)
        actions.addWidget(self.backup_button)
        actions.addWidget(self.restore_button)
        actions.addWidget(self.verify_button)
        actions.addWidget(self.verify_all_button)
        actions.addWidget(self.compare_button)
        actions.addWidget(self.export_compare_button)
        actions.addWidget(self.cleanup_button)
        actions.addWidget(self.export_report_button)
        actions.addWidget(self.developer_button)
        actions.addWidget(self.audit_button)
        actions.addWidget(self.export_dashboard_button)
        actions.addWidget(self.copy_dashboard_button)
        actions.addWidget(self.git_changes_button)
        actions.addWidget(self.refresh_project_button)
        actions.addWidget(self.autosave_pause_button)
        actions.addWidget(self.project_tools_button)
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
        self.table.setSortingEnabled(True)
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
        self.verify_shortcut = QShortcut(QKeySequence("Ctrl+Shift+V"), self)
        self.verify_shortcut.activated.connect(self._verify_selected)
        self.compare_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self.compare_shortcut.activated.connect(self._compare_selected)
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self._focus_archive_search)
        self.clear_search_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.clear_search_shortcut.activated.connect(self._clear_archive_search)
        self.terminal_shortcut = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        self.terminal_shortcut.activated.connect(self._open_project_terminal)
        self.copy_project_shortcut = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        self.copy_project_shortcut.activated.connect(self._copy_project_path)
        self.copy_checksum_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        self.copy_checksum_shortcut.activated.connect(self._copy_selected_checksum)
        self.archive_info_shortcut = QShortcut(QKeySequence("Ctrl+Shift+I"), self)
        self.archive_info_shortcut.activated.connect(self._show_selected_archive_info)
        self.manifest_shortcut = QShortcut(QKeySequence("Ctrl+Shift+M"), self)
        self.manifest_shortcut.activated.connect(self._export_selected_manifest)
        self.open_archive_shortcut = QShortcut(QKeySequence("Ctrl+Shift+O"), self)
        self.open_archive_shortcut.activated.connect(self._open_selected_archive)
        self.statusBar().showMessage(self._text("shortcut_help"))

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
        self._update_autosave_status()

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
        self.verify_all_button.setText(self._text("verify_all"))
        self.compare_button.setText(self._text("compare"))
        self.cleanup_button.setText(self._text("cleanup"))
        self.settings_button.setText(self._text("settings"))
        self._update_autosave_status()
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
        if hasattr(self, "autosave_countdown_timer"):
            self.autosave_countdown_timer.stop()
        self.autosave_timer = QTimer(self)
        self.next_autosave_at = None
        if self.settings.interval_minutes > 0:
            self.autosave_timer.timeout.connect(self._autosave)
            self.autosave_timer.start(self.settings.interval_minutes * 60 * 1000)
            self.next_autosave_at = time.monotonic() + self.settings.interval_minutes * 60
            self.autosave_countdown_timer = QTimer(self)
            self.autosave_countdown_timer.timeout.connect(self._update_autosave_status)
            self.autosave_countdown_timer.start(1000)
        if self.settings.backup_on_start:
            QTimer.singleShot(1200, lambda: self._start_backup_internal(automatic=True))
        self._update_autosave_status()

    def _update_autosave_status(self) -> None:
        if not hasattr(self, "autosave_status_label"):
            return
        if self.settings.interval_minutes <= 0 or self.next_autosave_at is None:
            status = self._text("autosave_off")
        else:
            remaining = max(0, int(self.next_autosave_at - time.monotonic()))
            minutes, seconds = divmod(remaining, 60)
            status = self._text(
                "autosave_next",
                minutes=self.settings.interval_minutes,
                remaining=f"{minutes:02d}:{seconds:02d}",
            )
        self.autosave_status_label.setText(self._text("autosave_status", status=status))

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
            context = git_context(self.manager.project_dir)
            if context["branch"]:
                dirty = "modified" if context["dirty"] else "clean"
                self.git_status_label.setText(
                    self._text("git_status", branch=context["branch"], commit=context["commit"], dirty=dirty)
                )
            else:
                self.git_status_label.setText(self._text("git_not_repo"))
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
            self.statusBar().showMessage(self._text("search_results", shown=len(archives), total=len(all_archives)))
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
        info_action = menu.addAction(self._text("archive_info"))
        manifest_action = menu.addAction(self._text("export_manifest"))
        rename_action = menu.addAction(self._text("rename_archive"))
        delete_action = menu.addAction(self._text("delete_archive"))
        checksum_action = menu.addAction(self._text("copy_checksum"))
        menu.addSeparator()
        project_action = menu.addAction(self._text("open_project_folder"))
        copy_project_action = menu.addAction(self._text("copy_project_path"))
        terminal_action = menu.addAction(self._text("open_terminal"))
        menu.addSeparator()
        copy_action = menu.addAction(self._text("copy_archive_path"))
        open_action = menu.addAction(self._text("open_archive_folder"))
        restore_files_action = menu.addAction(self._text("restore_files"))
        cloud_action = menu.addAction(self._text("cloud_upload"))
        selected = menu.exec_(self.table.viewport().mapToGlobal(position))
        if selected == info_action:
            self._show_archive_info(archive)
        elif selected == manifest_action:
            self._export_archive_manifest(archive)
        elif selected == rename_action:
            self._rename_archive(archive)
        elif selected == delete_action:
            self._delete_archive(archive)
        elif selected == checksum_action:
            self._copy_archive_checksum(archive)
        elif selected == project_action and self.manager:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.manager.project_dir)))
        elif selected == copy_project_action and self.manager:
            QApplication.clipboard().setText(str(self.manager.project_dir))
            self.statusBar().showMessage(self._text("project_path_copied"))
        elif selected == terminal_action:
            self._open_project_terminal()
        elif selected == copy_action:
            QApplication.clipboard().setText(str(archive))
            self.statusBar().showMessage(self._text("archive_path_copied"))
        elif selected == open_action:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(archive.parent)))
        elif selected == restore_files_action:
            self._restore_selected_files(archive)
        elif selected == cloud_action:
            self._upload_archive_to_cloud(archive)

    def _upload_selected_to_cloud(self) -> None:
        archive = self._selected_archive()
        if archive:
            self._upload_archive_to_cloud(archive)

    def _upload_archive_to_cloud(self, archive: Path) -> None:
        endpoint, accepted = QInputDialog.getText(self, self._text("cloud_upload"), self._text("cloud_url"))
        if not accepted or not endpoint.strip():
            return
        try:
            status = upload_archive(archive, endpoint.strip())
            self.statusBar().showMessage(self._text("cloud_uploaded", status=status))
        except (ValueError, RuntimeError, OSError) as exc:
            self._show_error(str(exc))

    def _show_archive_info(self, archive: Path) -> None:
        try:
            members = [item for item in self.manager.core.list_backup(archive) if not item.endswith("/")]
            details = next((item for item in archive_details(self.manager.backup_dir) if item[0] == archive), None)
            date, size = (details[1], details[2]) if details else ("—", format_bytes(archive.stat().st_size))
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            QMessageBox.information(
                self,
                self._text("archive_info"),
                self._text(
                    "archive_info_body", name=archive.name, date=date, size=size, files=len(members), path=archive
                ),
            )
            self.statusBar().showMessage(self._text("sha256", checksum=digest))
        except (BackupError, OSError, ValueError) as exc:
            self._show_error(str(exc))

    def _export_archive_manifest(self, archive: Path) -> None:
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("export_manifest"), f"{archive.stem}-manifest.txt"
        )
        if not destination:
            return
        try:
            members = [item for item in self.manager.core.list_backup(archive) if not item.endswith("/")]
            Path(destination).write_text(
                json.dumps({"archive": str(archive), "files": members}, indent=2) + "\n", encoding="utf-8"
            )
            self.statusBar().showMessage(self._text("export_manifest_done", path=destination))
        except (BackupError, OSError, ValueError) as exc:
            self._show_error(str(exc))

    def _rename_archive(self, archive: Path) -> None:
        name, accepted = QInputDialog.getText(
            self, self._text("rename_archive"), self._text("rename_prompt"), text=archive.name
        )
        if not accepted or not name.strip():
            return
        safe_name = Path(name.strip()).name
        if not safe_name.lower().endswith(".zip"):
            safe_name += ".zip"
        target = archive.with_name(safe_name)
        if target == archive or target.exists():
            self._show_error(self._text("error"))
            return
        try:
            archive.rename(target)
            self.statusBar().showMessage(self._text("rename_done"))
            self._refresh_backups()
        except OSError as exc:
            self._show_error(str(exc))

    def _delete_archive(self, archive: Path) -> None:
        if (
            QMessageBox.question(
                self,
                self._text("delete_archive"),
                self._text("delete_confirm", name=archive.name),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        try:
            archive.unlink()
            self.statusBar().showMessage(self._text("delete_done"))
            self._refresh_backups()
        except OSError as exc:
            self._show_error(str(exc))

    def _focus_archive_search(self) -> None:
        self.archive_search.setFocus()
        self.archive_search.selectAll()

    def _clear_archive_search(self) -> None:
        self.archive_search.clear()
        self.archive_search.setFocus()

    def _copy_archive_checksum(self, archive: Path) -> None:
        try:
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            QApplication.clipboard().setText(digest)
            self.statusBar().showMessage(self._text("checksum_copied"))
        except OSError as exc:
            self._show_error(str(exc))

    def _selected_archive(self) -> Path | None:
        row = self.table.currentRow()
        if row < 0 or not self.table.item(row, 0):
            self.statusBar().showMessage(self._text("no_archive_selected"))
            return None
        return Path(self.table.item(row, 0).data(Qt.UserRole))

    def _copy_project_path(self) -> None:
        if self.manager:
            QApplication.clipboard().setText(str(self.manager.project_dir))
            self.statusBar().showMessage(self._text("project_path_copied"))

    def _copy_selected_checksum(self) -> None:
        archive = self._selected_archive()
        if archive:
            self._copy_archive_checksum(archive)

    def _show_selected_archive_info(self) -> None:
        archive = self._selected_archive()
        if archive:
            self._show_archive_info(archive)

    def _export_selected_manifest(self) -> None:
        archive = self._selected_archive()
        if archive:
            self._export_archive_manifest(archive)

    def _open_selected_archive(self) -> None:
        archive = self._selected_archive()
        if archive:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(archive)))

    def _open_project_terminal(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        try:
            directory = str(self.manager.project_dir)
            if platform.system() == "Windows":
                subprocess.Popen(["cmd.exe", "/K"], cwd=directory)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", "Terminal", directory])
            else:
                subprocess.Popen(["x-terminal-emulator"], cwd=directory)
        except (OSError, ValueError) as exc:
            self._show_error(self._text("terminal_failed", error=exc))

    def _show_developer_dashboard(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        try:
            data = self._developer_dashboard_data()
            body = self._text(
                "developer_dashboard_body",
                **data,
            )
            QMessageBox.information(self, self._text("developer_dashboard"), body)
        except (OSError, ValueError) as exc:
            self._show_error(str(exc))

    def _developer_dashboard_data(self) -> dict[str, object]:
        files = self.manager.list_files()
        total_bytes = sum(path.stat().st_size for path in files)
        extensions = Counter(path.suffix.lower() or "[no extension]" for path in files)
        largest = max(files, key=lambda path: path.stat().st_size) if files else None
        context = git_context(self.manager.project_dir)
        return {
            "files": len(files),
            "size": format_bytes(total_bytes),
            "extensions": ", ".join(f"{key}: {value}" for key, value in extensions.most_common(6)) or "—",
            "largest": (
                f"{largest.relative_to(self.manager.project_dir)} ({format_bytes(largest.stat().st_size)})"
                if largest
                else "—"
            ),
            "branch": context.get("branch") or "—",
            "commit": context.get("commit") or "—",
            "dirty": "yes" if context.get("dirty") else "no",
            "backups": len(list(self.manager.backup_dir.glob("*.zip"))),
        }

    def _dashboard_body(self) -> str:
        return self._text("developer_dashboard_body", **self._developer_dashboard_data())

    def _export_dashboard(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("export_dashboard"), "codesaver-dashboard.json", "JSON files (*.json)"
        )
        if destination:
            Path(destination).write_text(
                json.dumps(self._developer_dashboard_data(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            self.statusBar().showMessage(self._text("dashboard_exported", path=destination))

    def _copy_dashboard(self) -> None:
        if self.manager:
            QApplication.clipboard().setText(self._dashboard_body())
            self.statusBar().showMessage(self._text("dashboard_copied"))

    def _open_git_changes(self) -> None:
        if self.manager:
            subprocess.Popen(
                ["git", "-C", str(self.manager.project_dir), "diff"],
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            )

    def _toggle_autosave_pause(self) -> None:
        if self.settings.interval_minutes <= 0:
            return
        paused = bool(getattr(self, "_autosave_paused", False))
        self._autosave_paused = not paused
        if self._autosave_paused:
            self.autosave_timer.stop()
            self.autosave_pause_button.setText(self._text("autosave_resume"))
        else:
            self._configure_autosave()
            self.autosave_pause_button.setText(self._text("autosave_pause"))

    def _export_file_inventory(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("export_inventory"), "codesaver-inventory.csv", "CSV files (*.csv)"
        )
        if not destination:
            return
        try:
            with Path(destination).open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["path", "bytes", "modified"])
                for path in self.manager.list_files():
                    stat = path.stat()
                    writer.writerow([str(path.relative_to(self.manager.project_dir)), stat.st_size, int(stat.st_mtime)])
            self.statusBar().showMessage(self._text("inventory_exported", path=destination))
        except OSError as exc:
            self._show_error(str(exc))

    def _show_exclusions(self) -> None:
        if not self.manager:
            return
        directories = ", ".join(sorted(self.settings.excluded_dirs)) or "—"
        extensions = ", ".join(sorted(self.settings.excluded_extensions)) or "—"
        QMessageBox.information(
            self,
            self._text("show_exclusions"),
            self._text("exclusions_body", directories=directories, extensions=extensions),
        )

    def _show_symlinks(self) -> None:
        if not self.manager:
            return
        links = [
            str(path.relative_to(self.manager.project_dir))
            for path in self.manager.project_dir.rglob("*")
            if path.is_symlink()
        ]
        QMessageBox.information(
            self, self._text("symlinks"), self._text("symlinks_body", count=len(links), items="\n".join(links) or "—")
        )

    def _copy_git_context(self) -> None:
        if self.manager:
            context = git_context(self.manager.project_dir)
            QApplication.clipboard().setText(json.dumps(context, ensure_ascii=False, indent=2))
            self.statusBar().showMessage(self._text("git_context_copied"))

    def _open_desktop_config(self) -> None:
        config_path = Path.home() / ".codesaver-desktop.json"
        if not config_path.exists():
            config_path.write_text(json.dumps(self.settings.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(config_path)))

    def _export_project_tree(self) -> None:
        if not self.manager:
            return
        destination, _ = QFileDialog.getSaveFileName(self, self._text("export_tree"), "project-tree.json")
        if not destination:
            return
        try:
            files = [str(path.relative_to(self.manager.project_dir).as_posix()) for path in self.manager.list_files()]
            Path(destination).write_text(
                json.dumps({"project": str(self.manager.project_dir), "files": files}, indent=2) + "\n",
                encoding="utf-8",
            )
            self.statusBar().showMessage(self._text("tree_exported", path=destination))
        except (OSError, ValueError) as exc:
            self._show_error(str(exc))

    def _copy_backup_command(self) -> None:
        if not self.manager:
            return
        command = (
            f'codesaver --project-dir "{self.manager.project_dir}" '
            f'--backup-dir "{self.manager.backup_dir}" --backup-now --verify'
        )
        QApplication.clipboard().setText(command)
        self.statusBar().showMessage(self._text("backup_command_copied"))

    def _show_largest_project_files(self) -> None:
        if not self.manager:
            return
        files = sorted(self.manager.list_files(), key=lambda path: path.stat().st_size, reverse=True)[:10]
        body = "\n".join(
            f"{format_bytes(path.stat().st_size)}  {path.relative_to(self.manager.project_dir)}" for path in files
        )
        QMessageBox.information(self, self._text("largest_project_files"), body or "—")

    def _show_unreadable_project_files(self) -> None:
        if not self.manager:
            return
        unreadable = []
        for path in self.manager.list_files():
            try:
                with path.open("rb"):
                    pass
            except OSError:
                unreadable.append(str(path.relative_to(self.manager.project_dir)))
        QMessageBox.information(self, self._text("unreadable_project_files"), "\n".join(unreadable) or "None")

    def _show_project_check(self) -> None:
        if not self.manager:
            return
        files = self.manager.list_files()
        unreadable = 0
        total_size = 0
        for path in files:
            try:
                total_size += path.stat().st_size
                with path.open("rb"):
                    pass
            except OSError:
                unreadable += 1
        QMessageBox.information(
            self,
            self._text("project_check"),
            self._text("project_check_body", files=len(files), unreadable=unreadable, size=format_bytes(total_size)),
        )

    def _find_duplicate_files(self) -> None:
        if not self.manager:
            return
        groups: dict[str, list[str]] = {}
        for path in self.manager.list_files():
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            groups.setdefault(digest, []).append(str(path.relative_to(self.manager.project_dir)))
        duplicates = [paths for paths in groups.values() if len(paths) > 1]
        QMessageBox.information(
            self, self._text("duplicates"), "\n\n".join("\n".join(paths) for paths in duplicates) or "None"
        )

    def _export_integrity_report(self) -> None:
        if not self.manager:
            return
        destination, _ = QFileDialog.getSaveFileName(self, self._text("integrity_report"), "archive-integrity.json")
        if not destination:
            return
        entries = []
        for archive, _date, _size in archive_details(self.manager.backup_dir):
            try:
                entries.append({"archive": str(archive), "ok": True, "files": self.manager.verify_backup(archive)})
            except (BackupError, OSError, ValueError) as exc:
                entries.append({"archive": str(archive), "ok": False, "error": str(exc)})
        try:
            Path(destination).write_text(json.dumps({"archives": entries}, indent=2) + "\n", encoding="utf-8")
            self.statusBar().showMessage(self._text("integrity_done", path=destination))
        except OSError as exc:
            self._show_error(str(exc))

    def _show_backup_free_space(self) -> None:
        if self.manager:
            usage = disk_usage(self.manager.backup_dir)
            QMessageBox.information(
                self,
                self._text("free_space"),
                self._text(
                    "free_space_body",
                    free=format_bytes(usage.free),
                    total=format_bytes(usage.total),
                    path=self.manager.backup_dir,
                ),
            )

    def _copy_restore_command(self) -> None:
        archive = self._selected_archive()
        if archive and self.manager:
            command = f'codesaver --project-dir "{self.manager.project_dir}" --restore "{archive}"'
            QApplication.clipboard().setText(command)
            self.statusBar().showMessage(self._text("restore_command_copied"))

    def _search_selected_archive_files(self) -> None:
        archive = self._selected_archive()
        if not archive or not self.manager:
            return
        query, accepted = QInputDialog.getText(
            self, self._text("search_archive_files"), self._text("search_archive_prompt")
        )
        if not accepted:
            return
        try:
            members = [item for item in self.manager.core.list_backup(archive) if query.casefold() in item.casefold()]
            QMessageBox.information(self, self._text("search_archive_files"), "\n".join(members) or "None")
        except (BackupError, OSError, ValueError) as exc:
            self._show_error(str(exc))

    def _compare_two_archives(self) -> None:
        first = self._selected_archive()
        if not first:
            return
        second, _ = QFileDialog.getOpenFileName(
            self, self._text("compare_archives_prompt"), str(first.parent), "ZIP archives (*.zip)"
        )
        if not second:
            return
        try:
            with zipfile.ZipFile(first) as first_zip, zipfile.ZipFile(second) as second_zip:
                left = {
                    item.filename: hashlib.sha256(first_zip.read(item)).hexdigest()
                    for item in first_zip.infolist()
                    if not item.is_dir()
                }
                right = {
                    item.filename: hashlib.sha256(second_zip.read(item)).hexdigest()
                    for item in second_zip.infolist()
                    if not item.is_dir()
                }
            QMessageBox.information(
                self,
                self._text("compare_archives"),
                self._text(
                    "compare_archives_body",
                    added=len(right.keys() - left.keys()),
                    removed=len(left.keys() - right.keys()),
                    changed=sum(1 for key in left.keys() & right.keys() if left[key] != right[key]),
                ),
            )
        except (BackupError, OSError, ValueError) as exc:
            self._show_error(str(exc))

    def _export_archive_hashes(self) -> None:
        archive = self._selected_archive()
        if not archive:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("export_archive_hashes"), f"{archive.stem}-hashes.csv"
        )
        if not destination:
            return
        try:
            import csv

            with Path(destination).open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(("path", "sha256"))
                with zipfile.ZipFile(archive) as opened:
                    for member in opened.infolist():
                        if not member.is_dir():
                            writer.writerow((member.filename, hashlib.sha256(opened.read(member)).hexdigest()))
            self.statusBar().showMessage(self._text("archive_hashes_done", path=destination))
        except (BackupError, OSError, ValueError, zipfile.BadZipFile) as exc:
            self._show_error(str(exc))

    def _show_unpacked_size(self) -> None:
        archive = self._selected_archive()
        if not archive:
            return
        try:
            with zipfile.ZipFile(archive) as opened:
                members = [item for item in opened.infolist() if not item.is_dir()]
                size = sum(item.file_size for item in members)
            QMessageBox.information(
                self,
                self._text("unpacked_size"),
                self._text("unpacked_size_body", name=archive.name, files=len(members), size=format_bytes(size)),
            )
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            self._show_error(str(exc))

    def _show_retention_preview(self) -> None:
        if not self.manager:
            return
        archives = sorted(self.manager.backup_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
        keep = self.settings.keep_last or len(archives)
        QMessageBox.information(
            self,
            self._text("retention_preview"),
            self._text("retention_body", kept=min(keep, len(archives)), remove=max(0, len(archives) - keep)),
        )

    def _copy_archive_manifest(self) -> None:
        archive = self._selected_archive()
        if archive and self.manager:
            members = [item for item in self.manager.core.list_backup(archive) if not item.endswith("/")]
            QApplication.clipboard().setText(
                json.dumps({"archive": str(archive), "files": members}, ensure_ascii=False, indent=2)
            )
            self.statusBar().showMessage(self._text("manifest_copied"))

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
        if self.settings.interval_minutes > 0:
            self.next_autosave_at = time.monotonic() + self.settings.interval_minutes * 60
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
            self._text("confirm_restore")
            + "\n\n"
            + self._text("restore_warning")
            + "\n\n"
            + self._text("restore_safety"),
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

    def _restore_selected_files(self, archive: Path) -> None:
        if not self.manager:
            return
        try:
            members = [item for item in self.manager.core.list_backup(archive) if not item.endswith("/")]
            value, accepted = QInputDialog.getMultiLineText(
                self,
                self._text("restore_files"),
                self._text("restore_files_prompt"),
                "\n".join(members),
            )
            if not accepted:
                return
            selected = [line.strip() for line in value.splitlines() if line.strip()]
            count = self.manager.restore_files(archive, selected, overwrite=True)
            self.statusBar().showMessage(self._text("restore_files_done", count=count))
            self._refresh_project_info()
        except (BackupError, OSError, ValueError) as exc:
            self._show_error(str(exc))

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

    def _compare_selected(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        row = self.table.currentRow()
        if row < 0:
            self.statusBar().showMessage(self._text("no_archive_selected"))
            return
        archive = Path(self.table.item(row, 0).data(Qt.UserRole))
        self._operation = "compare"
        self.statusBar().showMessage(self._text("compare_started"))
        self._set_busy(True)
        self.worker = BackupWorker(self.manager, "compare", archive, language=self._active_language)
        self._connect_worker()
        self.worker.start()

    def _export_compare_selected(self) -> None:
        if not self.manager:
            return
        row = self.table.currentRow()
        if row < 0:
            self.statusBar().showMessage(self._text("no_archive_selected"))
            return
        archive = Path(self.table.item(row, 0).data(Qt.UserRole))
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("export_compare"), "codesaver-compare-report.json", "JSON files (*.json)"
        )
        if not destination:
            return
        try:
            comparison = self.manager.compare_backup(archive)
            export_compare_report(archive, comparison, Path(destination))
            self.statusBar().showMessage(self._text("export_compare_done", path=destination))
        except (BackupError, OSError, ValueError) as exc:
            self._show_error(str(exc))

    def _verify_all(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        archives = [item[0] for item in archive_details(self.manager.backup_dir)]
        if not archives:
            self.statusBar().showMessage(self._text("no_archive_selected"))
            return
        self._operation = "verify_all"
        self.statusBar().showMessage(self._text("verify_all_started"))
        self._set_busy(True)
        self.progress.setValue(0)
        self.worker = BackupWorker(
            self.manager,
            "verify_all",
            language=self._active_language,
            archives=archives,
        )
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
        elif self._operation == "compare":
            result = json.loads(value)
            added = result["added"]
            modified = result["modified"]
            missing = result["missing"]
            self.statusBar().showMessage(
                self._text(
                    "compare_summary",
                    added=len(added),
                    modified=len(modified),
                    missing=len(missing),
                )
            )
            self._show_compare_result(result)
        elif self._operation == "verify_all":
            verified, total = str(value).split("/", 1)
            self.statusBar().showMessage(self._text("verify_all_done", verified=verified, total=total))
            self.tray.notify(self._text("title"), self._text("verify_all_done", verified=verified, total=total))
        else:
            self.statusBar().showMessage(self._text("restore_done", count=value))
        self._refresh_project_info()
        self._refresh_backups()

    def _show_compare_result(self, result: dict[str, list[str]]) -> None:
        def lines(items: list[str]) -> str:
            return "\n".join(f"  • {item}" for item in items) or "  —"

        body = self._text(
            "compare_details",
            added=lines(result["added"]),
            modified=lines(result["modified"]),
            missing=lines(result["missing"]),
        )
        QMessageBox.information(self, self._text("compare_title"), body)

    def _worker_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"{self._text('error')}: {message}")
        self.tray.notify(self._text("error"), message, error=True)
        self.tray.set_progress(None)
        self._show_error(message)

    def _set_busy(self, busy: bool) -> None:
        self.backup_button.setEnabled(not busy)
        self.restore_button.setEnabled(not busy)
        self.verify_button.setEnabled(not busy)
        self.verify_all_button.setEnabled(not busy)
        self.compare_button.setEnabled(not busy)
        self.export_compare_button.setEnabled(not busy)
        self.open_button.setEnabled(not busy)
        self.open_backups_button.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        self.settings_button.setEnabled(not busy)
        self.cleanup_button.setEnabled(not busy)
        self.export_report_button.setEnabled(not busy)

    def _export_report(self) -> None:
        if not self.manager:
            self.statusBar().showMessage(self._text("choose_project"))
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("export_report"), "codesaver-backup-report.json", "JSON files (*.json)"
        )
        if not destination:
            return
        try:
            export_backup_report(self.manager.backup_dir, Path(destination))
            self.statusBar().showMessage(self._text("export_report_done", path=destination))
        except (OSError, ValueError) as exc:
            self._show_error(str(exc))

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

    def _show_file_types(self) -> None:
        if not self.manager:
            return
        groups: dict[str, list[int]] = {}
        for path in self.manager.list_files():
            suffix = path.suffix.lower() or "[no extension]"
            groups.setdefault(suffix, [0, 0])
            groups[suffix][0] += 1
            groups[suffix][1] += path.stat().st_size
        body = "\n".join(f"{key}: {value[0]} files, {format_bytes(value[1])}" for key, value in sorted(groups.items()))
        QMessageBox.information(self, self._text("file_types"), body or "—")

    def _show_stale_files(self) -> None:
        if not self.manager:
            return
        days, accepted = QInputDialog.getInt(self, self._text("stale_files"), "Older than days:", 30, 0, 36500)
        if not accepted:
            return
        cutoff = time.time() - days * 86400
        files = [path for path in self.manager.list_files() if path.stat().st_mtime < cutoff]
        QMessageBox.information(
            self,
            self._text("stale_files"),
            "\n".join(str(path.relative_to(self.manager.project_dir)) for path in files) or "None",
        )

    def _show_archive_total(self) -> None:
        if not self.manager:
            return
        archives = list(self.manager.backup_dir.glob("*.zip"))
        total = sum(path.stat().st_size for path in archives)
        QMessageBox.information(
            self, self._text("archive_total"), f"Archives: {len(archives)}\nTotal: {format_bytes(total)}"
        )

    def _show_git_tags(self) -> None:
        if not self.manager:
            return
        result = subprocess.run(
            ["git", "-C", str(self.manager.project_dir), "tag", "--list"], capture_output=True, text=True, check=False
        )
        QMessageBox.information(self, self._text("git_tags"), result.stdout.strip() or "None")

    def _copy_backup_index(self) -> None:
        if not self.manager:
            return
        archives = sorted(self.manager.backup_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
        index = {
            "project": str(self.manager.project_dir),
            "backups": [
                {"path": str(path), "bytes": path.stat().st_size, "modified": path.stat().st_mtime} for path in archives
            ],
        }
        QApplication.clipboard().setText(json.dumps(index, ensure_ascii=False, indent=2))
        self.statusBar().showMessage(self._text("backup_index"))

    def _export_file_types(self) -> None:
        if not self.manager:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("export_file_types"), "file-types.csv", "CSV files (*.csv)"
        )
        if not destination:
            return
        groups: dict[str, list[int]] = {}
        for path in self.manager.list_files():
            suffix = path.suffix.lower() or "[no extension]"
            groups.setdefault(suffix, [0, 0])
            groups[suffix][0] += 1
            groups[suffix][1] += path.stat().st_size
        with Path(destination).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["extension", "files", "bytes"])
            writer.writerows([suffix, values[0], values[1]] for suffix, values in sorted(groups.items()))
        self.statusBar().showMessage(str(destination))

    def _show_archive_timeline(self) -> None:
        if not self.manager:
            return
        archives = sorted(self.manager.backup_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime)
        body = "\n".join(
            f"{datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds')}  {path.name}"
            for path in archives
        )
        QMessageBox.information(self, self._text("archive_timeline"), body or "None")

    def _show_empty_files(self) -> None:
        if not self.manager:
            return
        files = [
            str(path.relative_to(self.manager.project_dir))
            for path in self.manager.list_files()
            if path.stat().st_size == 0
        ]
        QMessageBox.information(self, self._text("empty_files"), "\n".join(files) or "None")

    def _copy_hash_inventory(self) -> None:
        if not self.manager:
            return
        entries = []
        for path in self.manager.list_files():
            try:
                entries.append(
                    {
                        "path": str(path.relative_to(self.manager.project_dir)),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
            except OSError:
                continue
        QApplication.clipboard().setText(
            json.dumps({"project": str(self.manager.project_dir), "files": entries}, ensure_ascii=False, indent=2)
        )
        self.statusBar().showMessage(self._text("copy_hash_inventory"))

    def _show_git_remotes(self) -> None:
        if not self.manager:
            return
        result = subprocess.run(
            ["git", "-C", str(self.manager.project_dir), "remote", "-v"], capture_output=True, text=True, check=False
        )
        QMessageBox.information(self, self._text("git_remotes"), result.stdout.strip() or "None")

    def _show_archive_ratio(self) -> None:
        archive = self._selected_archive()
        if not archive or not self.manager:
            return
        with zipfile.ZipFile(archive) as stream:
            unpacked = sum(item.file_size for item in stream.infolist() if not item.is_dir())
        ratio = 0 if unpacked == 0 else archive.stat().st_size / unpacked * 100
        QMessageBox.information(
            self,
            self._text("archive_ratio"),
            f"Archive: {format_bytes(archive.stat().st_size)}\nUnpacked: {format_bytes(unpacked)}\nStored ratio: {ratio:.1f}%",
        )

    def _export_timeline(self) -> None:
        if not self.manager:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("export_timeline"), "backup-timeline.csv", "CSV files (*.csv)"
        )
        if not destination:
            return
        archives = sorted(self.manager.backup_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime)
        with Path(destination).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["archive", "modified", "bytes"])
            writer.writerows(
                [path.name, datetime.fromtimestamp(path.stat().st_mtime).isoformat(), path.stat().st_size]
                for path in archives
            )
        self.statusBar().showMessage(str(destination))

    def _copy_file_list(self) -> None:
        if not self.manager:
            return
        files = [str(path.relative_to(self.manager.project_dir).as_posix()) for path in self.manager.list_files()]
        QApplication.clipboard().setText("\n".join(files))
        self.statusBar().showMessage(self._text("copy_file_list"))

    def _show_archive_dates(self) -> None:
        archive = self._selected_archive()
        if not archive:
            return
        with zipfile.ZipFile(archive) as stream:
            entries = [
                f"{item.date_time[0]:04d}-{item.date_time[1]:02d}-{item.date_time[2]:02d}  {item.filename}"
                for item in stream.infolist()
                if not item.is_dir()
            ]
        QMessageBox.information(self, self._text("archive_dates"), "\n".join(entries) or "None")

    def _copy_project_info(self) -> None:
        if not self.manager:
            return
        info = {
            "project": str(self.manager.project_dir),
            "files": len(self.manager.list_files()),
            "backup_dir": str(self.manager.backup_dir),
            "backups": len(list(self.manager.backup_dir.glob("*.zip"))),
        }
        QApplication.clipboard().setText(json.dumps(info, ensure_ascii=False, indent=2))
        self.statusBar().showMessage(self._text("copy_project_info"))

    def _show_recent_project_files(self) -> None:
        if not self.manager:
            return
        files = sorted(self.manager.list_files(), key=lambda path: path.stat().st_mtime, reverse=True)[:20]
        body = "\n".join(
            f"{datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='minutes')}  {path.relative_to(self.manager.project_dir)}"
            for path in files
        )
        QMessageBox.information(self, self._text("recent_project_files"), body or "None")

    def _export_archive_files(self) -> None:
        archive = self._selected_archive()
        if not archive:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("export_archive_files"), "archive-files.csv", "CSV files (*.csv)"
        )
        if not destination:
            return
        with zipfile.ZipFile(archive) as stream, Path(destination).open("w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerow(["path", "compressed_bytes", "uncompressed_bytes"])
            writer.writerows(
                [item.filename, item.compress_size, item.file_size] for item in stream.infolist() if not item.is_dir()
            )
        self.statusBar().showMessage(str(destination))

    def _compare_archive_project_size(self) -> None:
        archive = self._selected_archive()
        if not archive or not self.manager:
            return
        project_size = sum(path.stat().st_size for path in self.manager.list_files())
        QMessageBox.information(
            self,
            self._text("archive_project_size"),
            f"Project: {format_bytes(project_size)}\nArchive: {format_bytes(archive.stat().st_size)}",
        )

    def _show_archive_age(self) -> None:
        archive = self._selected_archive()
        if not archive:
            return
        age = max(0, time.time() - archive.stat().st_mtime)
        QMessageBox.information(self, self._text("archive_age"), f"{archive.name}\nAge: {age / 86400:.1f} days")

    def _copy_project_files_json(self) -> None:
        if not self.manager:
            return
        files = [
            {
                "path": str(path.relative_to(self.manager.project_dir)),
                "bytes": path.stat().st_size,
                "modified": path.stat().st_mtime,
            }
            for path in self.manager.list_files()
        ]
        QApplication.clipboard().setText(
            json.dumps({"project": str(self.manager.project_dir), "files": files}, ensure_ascii=False, indent=2)
        )
        self.statusBar().showMessage(self._text("copy_project_files_json"))

    def _show_archive_extensions(self) -> None:
        archive = self._selected_archive()
        if not archive:
            return
        with zipfile.ZipFile(archive) as stream:
            extensions = sorted(
                {
                    Path(item.filename).suffix.lower() or "[no extension]"
                    for item in stream.infolist()
                    if not item.is_dir()
                }
            )
        QMessageBox.information(self, self._text("archive_extensions"), "\n".join(extensions) or "None")

    def _export_project_sizes(self) -> None:
        if not self.manager:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("export_project_sizes"), "project-sizes.csv", "CSV files (*.csv)"
        )
        if not destination:
            return
        with Path(destination).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["path", "bytes"])
            writer.writerows(
                [str(path.relative_to(self.manager.project_dir)), path.stat().st_size]
                for path in self.manager.list_files()
            )
        self.statusBar().showMessage(str(destination))

    def _copy_backup_summary(self) -> None:
        if not self.manager:
            return
        archives = list(self.manager.backup_dir.glob("*.zip"))
        summary = {
            "project": str(self.manager.project_dir),
            "count": len(archives),
            "bytes": sum(path.stat().st_size for path in archives),
        }
        QApplication.clipboard().setText(json.dumps(summary, ensure_ascii=False, indent=2))
        self.statusBar().showMessage(self._text("copy_backup_summary"))

    def _find_archive_duplicates(self) -> None:
        archive = self._selected_archive()
        if not archive:
            return
        with zipfile.ZipFile(archive) as stream:
            groups: dict[str, list[str]] = {}
            for item in stream.infolist():
                if not item.is_dir():
                    groups.setdefault(hashlib.sha256(stream.read(item)).hexdigest(), []).append(item.filename)
        duplicates = ["\n".join(paths) for paths in groups.values() if len(paths) > 1]
        QMessageBox.information(self, self._text("archive_duplicates"), "\n\n".join(duplicates) or "None")

    def _copy_restore_preview(self) -> None:
        archive = self._selected_archive()
        if not archive:
            return
        with zipfile.ZipFile(archive) as stream:
            preview = {
                "archive": str(archive),
                "files": [item.filename for item in stream.infolist() if not item.is_dir()],
            }
        QApplication.clipboard().setText(json.dumps(preview, ensure_ascii=False, indent=2))
        self.statusBar().showMessage(self._text("copy_restore_preview"))

    def _export_archive_health_csv(self) -> None:
        if not self.manager:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("archive_health_csv"), "archive-health.csv", "CSV files (*.csv)"
        )
        if not destination:
            return
        with Path(destination).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["archive", "ok", "files", "error"])
            for archive, _date, _size in archive_details(self.manager.backup_dir):
                try:
                    writer.writerow([archive.name, True, self.manager.verify_backup(archive), ""])
                except (BackupError, OSError, ValueError) as exc:
                    writer.writerow([archive.name, False, 0, str(exc)])
        self.statusBar().showMessage(str(destination))

    def _show_project_dirs(self) -> None:
        if not self.manager:
            return
        dirs = sorted(
            {
                str(path.parent.relative_to(self.manager.project_dir))
                for path in self.manager.list_files()
                if path.parent != self.manager.project_dir
            }
        )
        QMessageBox.information(self, self._text("project_dirs"), "\n".join(dirs) or ".")

    def _copy_git_log(self) -> None:
        if not self.manager:
            return
        result = subprocess.run(
            ["git", "-C", str(self.manager.project_dir), "log", "-10", "--pretty=format:%h %ad %s", "--date=short"],
            capture_output=True,
            text=True,
            check=False,
        )
        QApplication.clipboard().setText(result.stdout)
        self.statusBar().showMessage(self._text("git_log_copy"))

    def _export_archive_ratio_csv(self) -> None:
        if not self.manager:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, self._text("archive_ratio_csv"), "archive-compression.csv", "CSV files (*.csv)"
        )
        if not destination:
            return
        with Path(destination).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["archive", "uncompressed_bytes", "stored_bytes", "saved_bytes"])
            for archive, _date, _size in archive_details(self.manager.backup_dir):
                with zipfile.ZipFile(archive) as source:
                    original = sum(item.file_size for item in source.infolist() if not item.is_dir())
                    stored = sum(item.compress_size for item in source.infolist() if not item.is_dir())
                writer.writerow([archive.name, original, stored, max(0, original - stored)])
        self.statusBar().showMessage(str(destination))

    def _show_backup_age_map(self) -> None:
        if not self.manager:
            return
        now = time.time()
        archives = sorted(self.manager.backup_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
        body = "\n".join(f"{path.name}: {(now - path.stat().st_mtime) / 86400:.1f} days" for path in archives)
        QMessageBox.information(self, self._text("backup_age_map"), body or "None")

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
        if hasattr(self, "autosave_countdown_timer"):
            self.autosave_countdown_timer.stop()
        event.accept()
