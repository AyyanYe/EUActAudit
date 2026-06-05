@echo off
echo ===================================================
echo     EU AI Act Auditor - Starting Backend Server
echo ===================================================
echo.
cd backend
call .\venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Virtual environment activation failed. Have you run setup_local.bat?
    cd ..
    pause
    exit /b 1
)

echo Starting FastAPI on http://localhost:8000 ...
uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause
