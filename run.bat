@echo off
setlocal

cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py %*
) else if exist "src\.venv\Scripts\python.exe" (
    "src\.venv\Scripts\python.exe" main.py %*
) else (
    python main.py %*
)

endlocal
