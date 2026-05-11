@echo off
setlocal

set "ROOT=%~dp0"
set "CLIENT=%ROOT%desktop-client"

echo.
echo Building dngscanner desktop EXE
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11+ and make sure it is on PATH.
  pause
  exit /b 1
)

if not exist "%CLIENT%\.venv\Scripts\python.exe" (
  python -m venv "%CLIENT%\.venv"
  if errorlevel 1 goto :fail
)

call "%CLIENT%\.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail

call "%CLIENT%\.venv\Scripts\pip.exe" install -r "%CLIENT%\requirements.txt" pyinstaller
if errorlevel 1 goto :fail

pushd "%CLIENT%"
call ".venv\Scripts\pyinstaller.exe" --clean --noconfirm --onefile --windowed --name dngscanner app.py
if errorlevel 1 (
  popd
  goto :fail
)
popd

echo.
echo EXE created at:
echo %CLIENT%\dist\dngscanner.exe
echo.
pause
exit /b 0

:fail
echo.
echo EXE build failed. Check the error above.
pause
exit /b 1
