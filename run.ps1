$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    & $VenvPython -m gitlab_cli @args
} else {
    python -m gitlab_cli @args
}
