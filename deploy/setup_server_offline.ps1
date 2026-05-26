param(
    [string]$InstallerPath = ".\\python-3.11.9-amd64.exe",
    [switch]$StartService = $true
)

$ErrorActionPreference = "Stop"

$bundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$installerFullPath = $InstallerPath

if (-not [System.IO.Path]::IsPathRooted($installerFullPath)) {
    $installerFullPath = Join-Path $bundleRoot $InstallerPath
}

function Resolve-Python311 {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            $ver = & $cmd.Source --version 2>&1
            if ($ver -match "Python 3\\.11\\.") {
                return $cmd.Source
            }
        } catch {
        }
    }

    $candidates = @(
        "C:\\Program Files\\Python311\\python.exe",
        "$env:LocalAppData\\Programs\\Python\\Python311\\python.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
}

$pythonExe = Resolve-Python311
if (-not $pythonExe) {
    if (-not (Test-Path $installerFullPath)) {
        throw "未找到 Python 安装包：$installerFullPath"
    }

    Write-Host "Installing Python 3.11 silently ..."
    $proc = Start-Process -FilePath $installerFullPath -ArgumentList @(
        "/quiet",
        "InstallAllUsers=1",
        "PrependPath=1",
        "Include_test=0"
    ) -Wait -PassThru

    if ($proc.ExitCode -ne 0) {
        throw "Python 安装失败，退出码：$($proc.ExitCode)"
    }

    $pythonExe = Resolve-Python311
    if (-not $pythonExe) {
        throw "Python 安装完成，但没有找到 python.exe"
    }
}

Write-Host "Using Python: $pythonExe"

& (Join-Path $bundleRoot "install_offline.ps1") -Python $pythonExe

if ($StartService) {
    & (Join-Path $bundleRoot "start_csvweb.ps1")
}
