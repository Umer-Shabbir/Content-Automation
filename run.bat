@echo off
setlocal

cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py %*
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py %*
) else if exist "src\.venv\Scripts\python.exe" (
    "src\.venv\Scripts\python.exe" main.py %*
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 main.py %*
    ) else (
        python main.py %*
    )
)

endlocal
