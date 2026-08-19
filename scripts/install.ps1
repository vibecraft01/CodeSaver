$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }

& $PythonBin -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "CodeSaver requires Python 3.9 or newer."
}

$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
& $PythonBin -m venv (Join-Path $ProjectDir ".venv")
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e $ProjectDir
Write-Host "CodeSaver installed. Run: .venv\Scripts\codesaver.exe"

