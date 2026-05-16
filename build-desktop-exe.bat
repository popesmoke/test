@echo off
setlocal
set "ROOT=%~dp0"
set "CLIENT=%ROOT%desktop-client"

echo.
echo Building single dngscanner.exe ^(Nuitka native compile^)
echo.

if not exist "%CLIENT%\build-secure-exe.bat" (
  echo Missing desktop-client\build-secure-exe.bat
  pause
  exit /b 1
)

call "%CLIENT%\build-secure-exe.bat"
exit /b %errorlevel%
