@echo off
setlocal
cd /d "%~dp0"
set "CSVWEB_HOST=0.0.0.0"
set "CSVWEB_PORT=8765"
"python\python.exe" app.py
pause
