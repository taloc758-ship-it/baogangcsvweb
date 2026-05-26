@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\setup_server_offline.ps1" -InstallerPath ".\python-3.11.9-amd64.exe"
pause
