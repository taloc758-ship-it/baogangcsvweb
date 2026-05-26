param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$bundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $bundleRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$packageDir = Join-Path $bundleRoot "packages"
$requirementsFile = Join-Path $bundleRoot "requirements.txt"

if (-not (Test-Path $packageDir)) {
    throw "未找到 packages 目录，请先在有网电脑执行 build_offline_bundle.ps1。"
}

Write-Host "Creating virtual environment ..."
& $Python -m venv $venvDir

Write-Host "Installing packages from local files ..."
& $venvPython -m pip install --no-index --find-links $packageDir -r $requirementsFile

Write-Host ""
Write-Host "Offline install complete."
Write-Host "Start command:"
Write-Host "  .\.venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8765"
