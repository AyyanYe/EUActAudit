@echo off
echo ===================================================
echo     EU AI Act Auditor - Local Setup (Non-Docker)
echo ===================================================
echo.

:: Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in your PATH. Please install Python 3.10+ and make sure it is added to your environment variables.
    pause
    exit /b 1
)

:: Check for Node
node -v >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js was not found in your PATH. Please install Node.js (v18+) and npm.
    pause
    exit /b 1
)

echo [1/3] Creating Python Virtual Environment in backend...
cd backend
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    cd ..
    pause
    exit /b 1
)

echo.
echo [2/3] Installing Backend Dependencies...
call .\venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    cd ..
    pause
    exit /b 1
)

echo.
echo Checking database and keys config...
python test_connection.py
cd ..

echo.
echo [3/3] Installing Frontend Dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install Node.js dependencies.
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo ===================================================
echo   Setup Complete!
echo.
echo   To test connections, run: cd backend ^& .\venv\Scripts\python.exe test_connection.py
echo   To start the backend, run: run_backend.bat
echo   To start the frontend, run: run_frontend.bat
echo ===================================================
pause
