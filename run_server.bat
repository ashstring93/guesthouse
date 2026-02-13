@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "SERVER_PORT=8000"
set "PYTHON_EXE="
set "PYTHON_ARGS="

if exist "%BACKEND_DIR%\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%BACKEND_DIR%\.env") do (
        if /I "%%A"=="PORT" set "SERVER_PORT=%%B"
    )
)

if exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    "%BACKEND_DIR%\venv\Scripts\python.exe" -c "import fastapi, dotenv" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=%BACKEND_DIR%\venv\Scripts\python.exe"
    ) else (
        echo [WARN] Ignoring backend\venv because required packages are missing.
    )
)

if not defined PYTHON_EXE if exist "%BACKEND_DIR%\.venv\Scripts\python.exe" (
    "%BACKEND_DIR%\.venv\Scripts\python.exe" -c "import fastapi, dotenv" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=%BACKEND_DIR%\.venv\Scripts\python.exe"
    ) else (
        echo [WARN] Ignoring backend\.venv because required packages are missing.
    )
)

if not defined PYTHON_EXE (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.12 -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_EXE=py"
            set "PYTHON_ARGS=-3.12"
        ) else (
            py -3 -c "import sys" >nul 2>nul
            if not errorlevel 1 (
                set "PYTHON_EXE=py"
                set "PYTHON_ARGS=-3"
            )
        )
    )
)

if not defined PYTHON_EXE (
    where python >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    )
)

if not defined PYTHON_EXE (
    echo [ERROR] Python executable was not found. Please install Python 3.12+ or create backend\venv.
    pause
    exit /b 1
)

netstat -ano | findstr /R /C:":%SERVER_PORT% .*LISTENING" >nul
if not errorlevel 1 (
    echo [ERROR] Port %SERVER_PORT% is already in use.
    echo [HINT] Stop the existing process or change PORT in backend\.env, for example PORT=8001.
    pause
    exit /b 1
)

echo Starting Mullebang-a House backend server...
echo.
echo [INFO] This script runs FastAPI on http://localhost:%SERVER_PORT%
echo [INFO] It serves frontend/index.html and frontend static assets from one server.
echo [INFO] Python command: %PYTHON_EXE% %PYTHON_ARGS%
echo.
echo Opening http://localhost:%SERVER_PORT% in your browser...
timeout /t 2 >nul
start http://localhost:%SERVER_PORT%
cd /d "%BACKEND_DIR%"
"%PYTHON_EXE%" %PYTHON_ARGS% server.py
pause
