$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
$taskPythonDir = Join-Path $taskProjectRoot '.venv\Scripts'
$taskPython = Join-Path $taskPythonDir 'python.exe'
$taskPython3 = Join-Path $taskPythonDir 'python3.exe'

if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Create .venv and install ml_model/requirements.txt before starting.'
}

# The existing API invokes python3; give it the project's Python on Windows.
if (-not (Test-Path -LiteralPath $taskPython3)) {
    Copy-Item -LiteralPath $taskPython -Destination $taskPython3
}
$env:PATH = "$taskPythonDir;$env:PATH"
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

Push-Location $taskProjectRoot
try {
    & npm.cmd run dev -- --hostname 127.0.0.1
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
