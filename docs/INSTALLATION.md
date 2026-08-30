# CodeSaver Installation Guide

CodeSaver provides a lightweight CLI and an optional PyQt5 Desktop application. Choose the installation path that matches how you want to use it.

## Requirements

- Windows 10/11, macOS, or Linux.
- Python 3.9 or newer for the CLI.
- Python 3.10 or newer plus PyQt5 for the Desktop application.

## Install from source

Clone the repository and create an isolated virtual environment:

```bash
git clone https://github.com/vibecraft01/CodeSaver.git
cd CodeSaver
python -m venv .venv
```

Activate it:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS/Linux
source .venv/bin/activate
```

Upgrade packaging tools and install the CLI:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Install the Desktop dependencies when needed:

```bash
python -m pip install -e ".[desktop]"
```

Verify the CLI installation:

```bash
codesaver --help
codesaver --project-dir . --project-summary
```

## Install release binaries

Download the matching files from the [GitHub Releases page](https://github.com/vibecraft01/CodeSaver/releases):

- Windows: run `CodeSaverDesktop-windows-x64.exe` or the CLI executable.
- macOS: extract `CodeSaverDesktop-macos.zip`, then open the application. If macOS blocks it, use **System Settings → Privacy & Security → Open Anyway**.
- Debian/Ubuntu: install `CodeSaverDesktop-linux-amd64.deb` with `sudo apt install ./CodeSaverDesktop-linux-amd64.deb`.

The release binaries do not require a separate Python installation.

## First backup

From a project directory, run:

```bash
codesaver --project-dir . --backup-now --verify
```

To choose a separate backup location:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

The Desktop application provides the same backup engine through its project selector and **Create Backup** action.

## Optional cloud upload

Cloud upload is disabled by default. Set a token in the environment and provide an S3-compatible endpoint:

```powershell
$env:CODESAVER_CLOUD_TOKEN = "your-token"
codesaver --cloud-upload .\backups\project_latest.zip --cloud-url https://storage.example/upload
```

```bash
export CODESAVER_CLOUD_TOKEN="your-token"
codesaver --cloud-upload ./backups/project_latest.zip --cloud-url https://storage.example/upload
```

Desktop users can select **Upload archive to cloud** from an archive context menu. Never commit tokens or place them in `.codesaver.json`.

## Troubleshooting

- If `python` is not recognized on Windows, reinstall Python with **Add Python to PATH** enabled.
- If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate the environment again.
- If the Desktop cannot start, install the Desktop extra with `python -m pip install -e ".[desktop]"` and verify that PyQt5 imports with `python -c "import PyQt5; print(PyQt5.__version__)"`.
- Use `codesaver --doctor --json` to inspect the backup directory, Git context, and Python runtime.
