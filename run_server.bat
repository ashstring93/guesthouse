@echo off
echo Starting local server for Mullebang-a House...
echo.
echo [INFO] Naver Maps API requires a web server (http://) to work correctly.
echo [INFO] Do not open html files directly (file://).
echo.
echo Opening http://localhost:8000 in your browser...
timeout /t 2 >nul
start http://localhost:8000
python -m http.server 8000
pause
