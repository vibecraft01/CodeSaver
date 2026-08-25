"""Core backup and restore functionality.

Only Python's standard library is used so CodeSaver works on Windows, Linux,
and macOS without extra runtime dependencies.
"""

from __future__ import annotations

from datetime import datetime
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import os
import tempfile
import time
from typing import Callable, Iterator, Optional, Union
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from .lang import translate

DEFAULT_EXCLUDED_DIRS = frozenset({".git", "__pycache__", "venv", ".venv", "env", ".env", ".tox", ".mypy_cache"})
ProgressCallback = Callable[[int, int, Path], None]
DetailedProgressCallback = Callable[[int, int, Path, int, int], None]
FileErrorCallback = Callable[[Path, BaseException], None]


def _gitignore_pattern_matches(candidate: str, rule: str, anchored: bool) -> bool:
    if "/" not in rule and not anchored:
        return fnmatchcase(candidate, rule) or any(fnmatchcase(part, rule) for part in candidate.split("/"))
    return fnmatchcase(candidate, rule)


class BackupError(RuntimeError):
    """Raised for an expected backup or restore error."""

    def __init__(self, key: str, **values: object) -> None:
        self.key = key
        self.values = values
        super().__init__(translate(key, "en", **values))

    def localized(self, language: str) -> str:
        return translate(self.key, language, **self.values)


class BackupManager:
    """Create and restore project snapshots."""

    def __init__(
        self,
        project_dir: Union[Path, str],
        backup_dir: Optional[Union[Path, str]] = None,
        excluded_dirs: Optional[set[str]] = None,
        excluded_extensions: Optional[set[str]] = None,
        excluded_patterns: Optional[set[str]] = None,
        compress: bool = False,
        max_size: Optional[int] = None,
        keep_last: Optional[int] = None,
        keep_days: Optional[int] = None,
        follow_symlinks: bool = False,
        use_gitignore: bool = True,
        file_error_callback: Optional[FileErrorCallback] = None,
    ) -> None:
        self.project_dir = Path(project_dir).expanduser().resolve()
        self.backup_dir = (
            Path(backup_dir).expanduser().resolve()
            if backup_dir
            else self.project_dir.parent / f"{self.project_dir.name}-backups"
        )
        self.excluded_dirs = frozenset(excluded_dirs or DEFAULT_EXCLUDED_DIRS)
        self.excluded_extensions = frozenset(item.lower() for item in (excluded_extensions or set()))
        self.excluded_patterns = frozenset(item.lower() for item in (excluded_patterns or set()))
        if max_size is not None and max_size < 0:
            raise ValueError("max_size must be non-negative")
        if keep_last is not None and keep_last < 1:
            raise ValueError("keep_last must be positive")
        if keep_days is not None and keep_days < 1:
            raise ValueError("keep_days must be positive")
        self.compress = compress
        self.max_size = max_size
        self.keep_last = keep_last
        self.keep_days = keep_days
        self.follow_symlinks = follow_symlinks
        self.use_gitignore = use_gitignore
        self.file_error_callback = file_error_callback
        self.last_cleanup_count = 0

    def _report_file_error(self, path: Path, error: BaseException) -> None:
        if self.file_error_callback:
            try:
                self.file_error_callback(path, error)
            except Exception:
                pass

    def _matches_exclusion_pattern(self, relative_path: Path) -> bool:
        candidate = relative_path.as_posix().lower()
        name = relative_path.name.lower()
        return any(fnmatchcase(candidate, pattern) or fnmatchcase(name, pattern) for pattern in self.excluded_patterns)

    def _validate_project(self) -> None:
        if not self.project_dir.exists():
            raise BackupError("errors.project_missing", project=self.project_dir)
        if not self.project_dir.is_dir():
            raise BackupError("errors.project_not_dir", project=self.project_dir)

    def iter_files(self) -> Iterator[Path]:
        """Yield files that belong in a snapshot, in stable order."""
        self._validate_project()
        backup_root = self.backup_dir
        gitignore_rules = self._load_gitignore_rules() if self.use_gitignore else []
        has_negated_rule = any(rule.startswith("!") for rule in gitignore_rules)
        for root, dirs, files in os.walk(
            self.project_dir, topdown=True, onerror=self._walk_error, followlinks=self.follow_symlinks
        ):
            root_path = Path(root)
            dirs[:] = sorted(
                name
                for name in dirs
                if name not in self.excluded_dirs
                and (root_path / name).resolve() != backup_root
                and not self._matches_exclusion_pattern((root_path / name).relative_to(self.project_dir))
                and (
                    not self.use_gitignore
                    or not self._gitignore_matches(
                        (root_path / name).relative_to(self.project_dir), True, gitignore_rules
                    )
                    or has_negated_rule
                )
            )
            for name in sorted(files):
                path = root_path / name
                relative_path = path.relative_to(self.project_dir)
                if (
                    (self.follow_symlinks or not path.is_symlink())
                    and not any(path.name.lower().endswith(extension) for extension in self.excluded_extensions)
                    and not self._matches_exclusion_pattern(relative_path)
                    and (not self.use_gitignore or not self._gitignore_matches(relative_path, False, gitignore_rules))
                ):
                    yield path

    def _load_gitignore_rules(self) -> list[str]:
        path = self.project_dir / ".gitignore"
        if not path.is_file():
            return []
        try:
            return [
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
        except PermissionError as exc:
            raise BackupError("errors.gitignore_failed", path=path, error=exc) from exc
        except (OSError, UnicodeError) as exc:
            raise BackupError("errors.gitignore_failed", path=path, error=exc) from exc

    @staticmethod
    def _gitignore_matches(relative_path: Path, is_dir: bool, rules: list[str]) -> bool:
        """Apply common root-level .gitignore rules using Git's last-match-wins behavior."""
        candidate = relative_path.as_posix().strip("/")
        ignored = False
        for raw_rule in rules:
            negated = raw_rule.startswith("!")
            rule = raw_rule[1:] if negated else raw_rule
            rule = rule.replace("\\", "/").strip()
            directory_only = rule.endswith("/")
            rule = rule.rstrip("/")
            anchored = rule.startswith("/")
            rule = rule.lstrip("/")
            if not rule:
                continue
            if directory_only:
                candidates = (
                    [candidate]
                    if is_dir
                    else ["/".join(relative_path.parts[:index]) for index in range(1, len(relative_path.parts))]
                )
                matches = any(_gitignore_pattern_matches(item, rule, anchored) for item in candidates)
            else:
                matches = _gitignore_pattern_matches(candidate, rule, anchored)
                if "/" not in rule and not anchored:
                    matches = matches or any(fnmatchcase(part, rule) for part in relative_path.parts)
            if matches:
                ignored = not negated
        return ignored

    @staticmethod
    def _walk_error(error: OSError) -> None:
        raise error

    def list_files(self) -> list[Path]:
        """Return the files included in the next backup."""
        files = []
        for path in self.iter_files():
            try:
                if self.max_size is None or path.stat().st_size <= self.max_size:
                    files.append(path)
            except PermissionError as exc:
                self._report_file_error(path, exc)
            except OSError as exc:
                self._report_file_error(path, exc)
        return files

    def create_backup(
        self,
        progress_callback: Optional[ProgressCallback] = None,
        detailed_progress_callback: Optional[DetailedProgressCallback] = None,
        include_manifest: bool = False,
    ) -> Path:
        """Create a timestamped ZIP archive and return its path.

        The archive is first written to a temporary file in the backup folder,
        then renamed into place so interrupted writes do not look like backups.
        """
        self._validate_project()
        temp_path: Optional[Path] = None
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            files = self.list_files()
            stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            destination = self.backup_dir / f"{self.project_dir.name}_{stamp}.zip"
            fd, temp_name = tempfile.mkstemp(prefix=".codesaver-", suffix=".tmp", dir=self.backup_dir)
            os.close(fd)
            temp_path = Path(temp_name)
            total_bytes = 0
            valid_files: list[Path] = []
            for path in files:
                try:
                    total_bytes += path.stat().st_size
                    valid_files.append(path)
                except (PermissionError, OSError) as exc:
                    self._report_file_error(path, exc)
            files = valid_files
            compression = ZIP_DEFLATED
            compresslevel = 9 if self.compress else None
            with ZipFile(temp_path, "w", compression=compression, compresslevel=compresslevel) as archive:
                if not files and progress_callback:
                    progress_callback(0, 0, self.project_dir)
                if not files and detailed_progress_callback:
                    detailed_progress_callback(0, 0, self.project_dir, 0, 0)
                processed_bytes = 0
                manifest: list[dict[str, object]] = []
                for current, path in enumerate(files, start=1):
                    try:
                        archive.write(path, path.relative_to(self.project_dir).as_posix())
                    except (PermissionError, OSError) as exc:
                        self._report_file_error(path, exc)
                        continue
                    try:
                        processed_bytes += path.stat().st_size
                        if include_manifest:
                            digest = hashlib.sha256()
                            with path.open("rb") as source:
                                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                                    digest.update(chunk)
                            manifest.append(
                                {
                                    "path": path.relative_to(self.project_dir).as_posix(),
                                    "size": path.stat().st_size,
                                    "sha256": digest.hexdigest(),
                                }
                            )
                    except (PermissionError, OSError) as exc:
                        self._report_file_error(path, exc)
                        continue
                    if progress_callback:
                        progress_callback(current, len(files), path)
                    if detailed_progress_callback:
                        detailed_progress_callback(current, len(files), path, processed_bytes, total_bytes)
                if include_manifest:
                    archive.writestr(
                        ".codesaver-manifest.json",
                        json.dumps(
                            {"version": 1, "algorithm": "sha256", "files": manifest},
                            ensure_ascii=False,
                            indent=2,
                        ),
                    )
            temp_path.replace(destination)
            self.last_cleanup_count = self.cleanup_old_backups()
            return destination
        except PermissionError as exc:
            if temp_path:
                temp_path.unlink(missing_ok=True)
            raise BackupError("errors.permission", path=getattr(exc, "filename", None) or self.backup_dir) from exc
        except (OSError, ValueError) as exc:
            if temp_path:
                temp_path.unlink(missing_ok=True)
            raise BackupError("errors.create_failed", error=exc) from exc

    def verify_backup(self, archive_path: Union[Path, str]) -> int:
        """Validate ZIP structure and CRCs, returning the member count."""
        archive = Path(archive_path).expanduser().resolve()
        if not archive.is_file():
            raise BackupError("errors.archive_missing", archive=archive)
        try:
            with ZipFile(archive, "r") as source:
                corrupted_member = source.testzip()
                if corrupted_member:
                    raise BackupError("errors.invalid_zip", archive=archive)
                if ".codesaver-manifest.json" in source.namelist():
                    try:
                        manifest = json.loads(source.read(".codesaver-manifest.json").decode("utf-8"))
                        for item in manifest.get("files", []):
                            member = str(item["path"])
                            digest = hashlib.sha256(source.read(member)).hexdigest()
                            if digest != item["sha256"]:
                                raise BackupError("errors.invalid_zip", archive=archive)
                    except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
                        raise BackupError("errors.invalid_zip", archive=archive) from exc
                return len(source.infolist())
        except BackupError:
            raise
        except (BadZipFile, EOFError, RuntimeError) as exc:
            raise BackupError("errors.invalid_zip", archive=archive) from exc
        except OSError as exc:
            raise BackupError("errors.restore_failed", error=exc) from exc

    def list_backup(self, archive_path: Union[Path, str]) -> list[str]:
        """Return sorted archive members after validating the ZIP container."""
        archive = Path(archive_path).expanduser().resolve()
        if not archive.is_file():
            raise BackupError("errors.archive_missing", archive=archive)
        try:
            with ZipFile(archive, "r") as source:
                if source.testzip():
                    raise BackupError("errors.invalid_zip", archive=archive)
                return sorted(source.namelist())
        except BackupError:
            raise
        except (BadZipFile, EOFError, RuntimeError) as exc:
            raise BackupError("errors.invalid_zip", archive=archive) from exc
        except OSError as exc:
            raise BackupError("errors.restore_failed", error=exc) from exc

    def compare_backup(self, archive_path: Union[Path, str]) -> dict[str, list[str]]:
        """Compare the current project state with a ZIP snapshot."""
        archive = Path(archive_path).expanduser().resolve()
        self.verify_backup(archive)
        current_paths = {path.relative_to(self.project_dir).as_posix(): path for path in self.list_files()}
        try:
            with ZipFile(archive, "r") as source:
                archived_paths = {
                    info.filename
                    for info in source.infolist()
                    if not info.is_dir() and info.filename != ".codesaver-manifest.json"
                }
                added = sorted(set(current_paths) - archived_paths)
                missing = sorted(archived_paths - set(current_paths))
                modified: list[str] = []
                for name in sorted(set(current_paths) & archived_paths):
                    digest = hashlib.sha256()
                    with current_paths[name].open("rb") as current_file:
                        for chunk in iter(lambda: current_file.read(1024 * 1024), b""):
                            digest.update(chunk)
                    if digest.hexdigest() != hashlib.sha256(source.read(name)).hexdigest():
                        modified.append(name)
                return {"added": added, "modified": modified, "missing": missing}
        except (BadZipFile, EOFError, RuntimeError) as exc:
            raise BackupError("errors.invalid_zip", archive=archive) from exc
        except (OSError, ValueError) as exc:
            raise BackupError("errors.restore_failed", error=exc) from exc

    def cleanup_old_backups(self) -> int:
        """Keep only the configured number of backups for this project."""
        if self.keep_last is None and self.keep_days is None:
            return 0
        prefix = f"{self.project_dir.name}_"
        try:
            archives = sorted(
                (
                    path
                    for path in self.backup_dir.iterdir()
                    if path.is_file() and path.suffix.lower() == ".zip" and path.name.startswith(prefix)
                ),
                key=lambda path: (path.stat().st_mtime, path.name),
                reverse=True,
            )
            removed = 0
            if self.keep_days is not None:
                cutoff = time.time() - self.keep_days * 86400
                aged = [archive for archive in archives if archive.stat().st_mtime < cutoff]
                for archive in aged:
                    archive.unlink()
                    removed += 1
                archives = [archive for archive in archives if archive.exists()]
            if self.keep_last is not None:
                old_archives = archives[self.keep_last :]
            else:
                old_archives = []
            for archive in old_archives:
                archive.unlink()
                removed += 1
            return removed
        except PermissionError as exc:
            raise BackupError("errors.cleanup_failed", path=getattr(exc, "filename", None) or self.backup_dir) from exc
        except OSError as exc:
            raise BackupError("errors.cleanup_failed", path=self.backup_dir, error=exc) from exc

    def restore_backup(self, archive_path: Union[Path, str], overwrite: bool = False) -> int:
        """Restore an archive into the project directory and return file count.

        Zip member paths are validated to prevent path traversal outside the
        target directory.
        """
        self._validate_project()
        archive = Path(archive_path).expanduser().resolve()
        if not archive.is_file():
            raise BackupError("errors.archive_missing", archive=archive)
        count = 0
        try:
            with ZipFile(archive, "r") as source:
                corrupted_member = source.testzip()
                if corrupted_member:
                    raise BackupError("errors.invalid_zip", archive=archive)
                target_root = self.project_dir.resolve()
                for member in source.infolist():
                    target = (target_root / member.filename).resolve()
                    if target != target_root and target_root not in target.parents:
                        raise BackupError("errors.unsafe_path", member=member.filename)
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    if target.exists() and not overwrite:
                        raise BackupError("errors.file_exists", path=target)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(member) as input_file, target.open("wb") as output_file:
                        output_file.write(input_file.read())
                    count += 1
        except BackupError:
            raise
        except PermissionError as exc:
            raise BackupError("errors.permission", path=getattr(exc, "filename", None) or self.project_dir) from exc
        except (BadZipFile, EOFError, RuntimeError) as exc:
            raise BackupError("errors.invalid_zip", archive=archive) from exc
        except (OSError, ValueError) as exc:
            raise BackupError("errors.restore_failed", error=exc) from exc
        return count

    def restore_files(self, archive_path: Union[Path, str], members: list[str], overwrite: bool = False) -> int:
        """Restore only selected safe files from an archive."""
        self._validate_project()
        archive = Path(archive_path).expanduser().resolve()
        requested = {str(member).replace("\\", "/") for member in members if str(member).strip()}
        if not archive.is_file() or not requested:
            raise BackupError("errors.archive_missing", archive=archive)
        count = 0
        try:
            with ZipFile(archive, "r") as source:
                if source.testzip():
                    raise BackupError("errors.invalid_zip", archive=archive)
                target_root = self.project_dir.resolve()
                available = {info.filename: info for info in source.infolist() if not info.is_dir()}
                for name in sorted(requested):
                    member = available.get(name)
                    if member is None or name == ".codesaver-manifest.json":
                        continue
                    target = (target_root / name).resolve()
                    if target_root not in target.parents:
                        raise BackupError("errors.unsafe_path", member=name)
                    if target.exists() and not overwrite:
                        raise BackupError("errors.file_exists", path=target)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(member) as input_file, target.open("wb") as output_file:
                        output_file.write(input_file.read())
                    count += 1
        except BackupError:
            raise
        except (BadZipFile, EOFError, RuntimeError) as exc:
            raise BackupError("errors.invalid_zip", archive=archive) from exc
        except (OSError, ValueError) as exc:
            raise BackupError("errors.restore_failed", error=exc) from exc
        return count
