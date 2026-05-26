param(
    [string]$HostAddress = "0.0.0.0",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$bundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $bundleRoot "python\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "未找到 python\\python.exe，说明便携包不完整。"
}

$env:CSVWEB_HOST = $HostAddress
$env:CSVWEB_PORT = "$Port"

Set-Location $bundleRoot
& $pythonExe "app.py"
