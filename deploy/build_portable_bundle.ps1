param(
    [string]$PythonHome = "C:\Users\Administrator\AppData\Local\Programs\Python\Python311",
    [string]$OutputDir = "portable_bundle"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$bundleRoot = Join-Path $projectRoot $OutputDir
$pythonRoot = Join-Path $bundleRoot "python"
$zipPath = Join-Path $projectRoot "portable_bundle.zip"
$pythonExe = Join-Path $pythonRoot "python.exe"

if (Test-Path $bundleRoot) {
    Remove-Item $bundleRoot -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $bundleRoot | Out-Null

Write-Host "Copying application files ..."
Copy-Item (Join-Path $projectRoot "app.py") $bundleRoot -Force
Copy-Item (Join-Path $projectRoot "requirements.txt") $bundleRoot -Force
Copy-Item (Join-Path $projectRoot "static") $bundleRoot -Recurse -Force
Copy-Item (Join-Path $projectRoot "工艺规程文件") $bundleRoot -Recurse -Force
Copy-Item (Join-Path $projectRoot "deploy\\run_portable.bat") $bundleRoot -Force
Copy-Item (Join-Path $projectRoot "deploy\\run_portable.ps1") $bundleRoot -Force
Copy-Item (Join-Path $projectRoot "deploy\\README-便携部署.md") $bundleRoot -Force

Write-Host "Copying local Python runtime ..."
Copy-Item $PythonHome $pythonRoot -Recurse -Force

Write-Host "Installing dependencies into copied Python runtime ..."
& $pythonExe -m pip install fastapi uvicorn[standard]

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Write-Host "Creating archive $zipPath ..."
Compress-Archive -Path (Join-Path $bundleRoot "*") -DestinationPath $zipPath

Write-Host ""
Write-Host "Portable bundle ready:"
Write-Host "  Folder: $bundleRoot"
Write-Host "  Zip:    $zipPath"
