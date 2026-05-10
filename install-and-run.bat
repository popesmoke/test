@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "CLIENT=%ROOT%desktop-client"
set "DASHBOARD=%ROOT%web-dashboard"

echo.
echo Secure Remote Diagnostic - install and run
echo Root: %ROOT%
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11+ and make sure it is on PATH.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found. Install Node.js LTS and make sure npm is on PATH.
  pause
  exit /b 1
)

echo [1/5] Preparing backend virtual environment...
if not exist "%BACKEND%\.venv\Scripts\python.exe" (
  python -m venv "%BACKEND%\.venv"
  if errorlevel 1 goto :fail
)

echo [2/5] Installing backend dependencies...
call "%BACKEND%\.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
call "%BACKEND%\.venv\Scripts\pip.exe" install -r "%BACKEND%\requirements.txt"
if errorlevel 1 goto :fail

echo [3/5] Preparing desktop client virtual environment...
if not exist "%CLIENT%\.venv\Scripts\python.exe" (
  python -m venv "%CLIENT%\.venv"
  if errorlevel 1 goto :fail
)

echo [4/5] Installing desktop client dependencies...
call "%CLIENT%\.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
call "%CLIENT%\.venv\Scripts\pip.exe" install -r "%CLIENT%\requirements.txt"
if errorlevel 1 goto :fail

echo [5/5] Installing dashboard dependencies...
pushd "%DASHBOARD%"
call npm install
if errorlevel 1 (
  popd
  goto :fail
)
popd

echo.
echo Starting backend, dashboard, and desktop client...
echo.

start "Diagnostic Backend" "%ROOT%start-backend.bat"
timeout /t 3 /nobreak >nul

start "Checker Dashboard" "%ROOT%start-dashboard.bat"
timeout /t 2 /nobreak >nul

start "Desktop Diagnostic Client" "%ROOT%start-desktop-app.bat"

echo Backend:   http://localhost:8000
echo Dashboard: http://localhost:3000
echo.
echo Default checker login:
echo Email:    checker@example.com
echo Password: change-me
echo.
pause
exit /b 0

:fail
echo.
echo Install or startup failed. Check the error above.
pause
exit /b 1
