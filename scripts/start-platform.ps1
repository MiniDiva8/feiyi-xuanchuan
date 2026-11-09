param(
    [switch]$Install,
    [ValidateRange(1024,65535)][int]$Port = 8010,
    [switch]$OpenBrowser
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$portablePython = Join-Path $projectRoot '.artifacts\runtime\python312\python.exe'
if (Test-Path -LiteralPath $portablePython) {
    $pythonPath = $portablePython
}
$webPath = Join-Path $projectRoot 'apps\web'
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath $pythonPath)) {
    & python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
    if ($LASTEXITCODE -ne 0) { throw '需要 Python 3.12 或更高版本，请安装后重试。' }
    & python -m venv (Join-Path $projectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw '无法创建虚拟环境，请安装 Python 3.12+。' }
    $Install = $true
}
& $pythonPath -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if ($LASTEXITCODE -ne 0) { throw '项目运行环境版本过低，需要 Python 3.12 或更高版本。' }
if ($Install) {
    & $pythonPath -m pip install -r (Join-Path $projectRoot 'services\api\requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw '后端依赖安装失败。' }
    Push-Location -LiteralPath $webPath
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败，请安装 Node.js 22.12+。' }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw '前端构建失败。' }
    } finally { Pop-Location }
}
if (-not (Test-Path -LiteralPath (Join-Path $webPath 'dist\index.html'))) {
    throw '尚未构建前端。请执行 powershell -File scripts/start-platform.ps1 -Install。'
}
$envFile = Join-Path $projectRoot '.env'
if (Test-Path -LiteralPath $envFile) {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match '^\s*(MARKETING_AI_[A-Z_]+|DATABASE_URL|SESSION_SECURE|TRUSTED_ORIGINS|STORAGE_PATH)\s*=\s*(.*?)\s*$') {
            $settingName = $Matches[1]
            $settingValue = $Matches[2].Trim().Trim([char]34).Trim([char]39)
            [Environment]::SetEnvironmentVariable($settingName, $settingValue, 'Process')
        }
    }
}
$env:PYTHONPATH = (Join-Path $projectRoot 'services\api') + ';' + (Join-Path $projectRoot 'services\marketing-ai')
Write-Output ('非遗商家营销工作台: http://127.0.0.1:' + $Port)
Write-Output '首次使用请注册自己的账号与商家空间。Ctrl+C 停止服务；数据保留在 .data。'
if ($OpenBrowser) { Start-Process ('http://127.0.0.1:' + $Port) }
& $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
