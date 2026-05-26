param(
    [string]$HostAddress = "0.0.0.0",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$bundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $bundleRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "未找到 .venv\\Scripts\\python.exe，请先执行 install_offline.ps1。"
}

Set-Location $bundleRoot
& $venvPython -m uvicorn app:app --host $HostAddress --port $Port
