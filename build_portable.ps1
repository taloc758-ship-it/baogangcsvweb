param(
    [string]$OutputDir = "dist\\csvweb",
    [string]$Name = "csvweb"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw "未找到 pyinstaller，请先执行: pip install pyinstaller"
}

if (Test-Path $OutputDir) {
    Remove-Item $OutputDir -Recurse -Force
}

pyinstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name $Name `
    launcher.py

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Copy-Item app.py $OutputDir -Force
Copy-Item static $OutputDir -Recurse -Force
Copy-Item 工艺规程文件 $OutputDir -Recurse -Force

if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force
}

if (Test-Path "$Name.spec") {
    Remove-Item "$Name.spec" -Force
}

Write-Host "Build done: $PWD\$OutputDir"
