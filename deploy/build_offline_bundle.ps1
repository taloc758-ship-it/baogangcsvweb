param(
    [string]$Python = "python",
    [string]$OutputDir = "offline_bundle",
    [string]$PythonInstaller = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$bundleRoot = Join-Path $projectRoot $OutputDir
$packageDir = Join-Path $bundleRoot "packages"

if (Test-Path $bundleRoot) {
    Remove-Item $bundleRoot -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $bundleRoot | Out-Null
New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

Write-Host "Downloading Python packages to $packageDir ..."
& $Python -m pip download -r (Join-Path $projectRoot "requirements.txt") -d $packageDir

Write-Host "Copying project files ..."
Copy-Item (Join-Path $projectRoot "app.py") $bundleRoot -Force
Copy-Item (Join-Path $projectRoot "requirements.txt") $bundleRoot -Force
Copy-Item (Join-Path $projectRoot "static") $bundleRoot -Recurse -Force
Copy-Item (Join-Path $projectRoot "工艺规程文件") $bundleRoot -Recurse -Force
Copy-Item (Join-Path $projectRoot "deploy\install_offline.ps1") $bundleRoot -Force
Copy-Item (Join-Path $projectRoot "deploy\start_csvweb.ps1") $bundleRoot -Force
Copy-Item (Join-Path $projectRoot "deploy\setup_server_offline.ps1") $bundleRoot -Force
Copy-Item (Join-Path $projectRoot "deploy\setup_and_run.bat") $bundleRoot -Force
Copy-Item (Join-Path $projectRoot "deploy\README-离线部署.md") $bundleRoot -Force

if ($PythonInstaller) {
    if (-not (Test-Path $PythonInstaller)) {
        throw "未找到 Python 安装包：$PythonInstaller"
    }
    Write-Host "Copying Python installer ..."
    Copy-Item $PythonInstaller $bundleRoot -Force
}

$zipPath = Join-Path $projectRoot "offline_bundle.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Write-Host "Creating archive $zipPath ..."
Compress-Archive -Path (Join-Path $bundleRoot "*") -DestinationPath $zipPath

Write-Host ""
Write-Host "Offline bundle ready:"
Write-Host "  Folder: $bundleRoot"
Write-Host "  Zip:    $zipPath"
