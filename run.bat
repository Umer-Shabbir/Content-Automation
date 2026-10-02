@echo off
setlocal

cd /d "%~dp0"

if exist "src\.venv\Scripts\python.exe" (
    "src\.venv\Scripts\python.exe" main.py %*
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py %*
) else (
    py -3.12 main.py %*
)

endlocal
