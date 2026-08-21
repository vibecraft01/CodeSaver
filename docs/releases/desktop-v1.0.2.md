# CodeSaver Desktop v1.0.2

This release improves project selection, recovery safety, storage visibility, and background feedback.

## What's new

- Drag and drop a project folder onto the application window.
- Keep and select the five most recently opened projects.
- Confirm restore operations with an explicit overwrite warning.
- Warn before backups when the destination disk has less than 1 GB free.
- Add a confirmed “Clean old backups” action using the configured retention policy.
- Show backup percentage progress in the system-tray icon.
- Report skipped unreadable files and unexpected archive errors clearly.
- Harden PyInstaller Qt plugin discovery for Windows packaged builds.

## Local validation

- Full test suite: 30 tests passed.
- Black and Flake8 passed.
- Rebuilt `dist/CodeSaverDesktop.exe` locally.
- Packaged Windows executable smoke-tested successfully.
