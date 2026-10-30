# PowerShell convenience wrapper. No machine-wide policy or credentials are changed.
$ErrorActionPreference = 'Stop'
$taskArguments = $args
$taskPython = Get-Command python -ErrorAction SilentlyContinue
if (-not $taskPython) {
    throw 'Python 3.11+ is required. Alternatively use python scripts/collab.py directly.'
}
Push-Location -LiteralPath $PSScriptRoot
try {
    & $taskPython.Source (Join-Path $PSScriptRoot 'scripts\collab.py') @taskArguments
    $taskExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $taskExitCode
