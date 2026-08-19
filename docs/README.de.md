# CodeSaver

CodeSaver ist ein plattformübergreifendes Konsolenprogramm zum Erstellen zeitgestempelter ZIP-Snapshots von Codeprojekten. Es verwendet nur die Python-Standardbibliothek, speichert automatisch im Hintergrund und erkennt die Systemsprache.

## Schnellstart

```bash
python -m venv .venv
python -m pip install -e .
codesaver
```

Eine einzelne Sicherung ohne Menü erstellen:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

Ein Archiv wiederherstellen:

```bash
codesaver --project-dir ./my-project --restore ./backups/my-project_2026-01-20_14-30-00.zip --overwrite
```

Das Standardintervall beträgt 600 Sekunden. Mit `--no-autosave` wird die automatische Sicherung deaktiviert, mit `--interval 300` geändert und mit `--language de` die Sprache festgelegt. `.git`, `__pycache__`, virtuelle Umgebungen und Tool-Caches werden standardmäßig ausgeschlossen.

Die vollständige Dokumentation steht im [Haupt-README](../README.md). Lizenz: MIT.

