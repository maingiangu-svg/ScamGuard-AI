$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Create .venv and install ml_model/requirements.txt before starting.'
}
$env:PYTHON_EXECUTABLE = $taskPython
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
Push-Location $taskProjectRoot
try {
    & npm.cmd run dev -- --hostname 127.0.0.1
    exit $LASTEXITCODE
} finally { Pop-Location }
