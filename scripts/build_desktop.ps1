$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir
$VenvDir = Join-Path $ProjectDir ".desktop-build-venv"
python -m venv $VenvDir
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e ".[desktop,release]"
& $VenvPython -m PyInstaller --clean --noconfirm --onefile --windowed --name CodeSaverDesktop scripts\build_desktop_entry.py
Write-Host "Built dist\CodeSaverDesktop.exe"
