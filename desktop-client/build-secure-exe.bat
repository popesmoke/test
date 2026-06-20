@echo off
setlocal EnableDelayedExpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo Virello Scanner — single EXE build (Nuitka native compile)
echo.

if "%DNG_API_URL%"=="" if "%DIAGNOSTIC_API_URL%"=="" (
  echo No DNG_API_URL set — using baked-in default API ^(set DNG_API_URL for production^).
  set "DNG_ALLOW_DEFAULT_API=1"
)

where python >nul 2>nul
if errorlevel 1 (
  echo Python not found on PATH. Use Python 3.11 or 3.12 for best results.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto :fail
)

echo Installing build dependencies...
call .venv\Scripts\python.exe -m pip install --upgrade pip -q
call .venv\Scripts\pip.exe install -r requirements-build.txt -q
if errorlevel 1 goto :fail

echo [1/5] Baking API URL...
call .venv\Scripts\python.exe scripts\generate_build_config.py
if errorlevel 1 goto :fail

echo [2/5] Preparing icon assets...
call .venv\Scripts\python.exe scripts\prepare_assets.py
if errorlevel 1 goto :fail

echo [3/5] Preparing build entry...
call .venv\Scripts\python.exe scripts\prepare_build_entry.py
if errorlevel 1 goto :fail

if exist "embedded_build_config.py" copy /Y "embedded_build_config.py" "_build_obf\" >nul

set "ICON_ARG="
if exist "%ROOT%assets\scanner-icon.ico" set "ICON_ARG=--windows-icon-from-ico=..\assets\scanner-icon.ico"

set "DATA_ARG="
if exist "%ROOT%assets\scanner-icon.png" set "DATA_ARG=--include-data-files=..\assets\scanner-icon.png=assets\scanner-icon.png --include-data-files=..\assets\scanner-icon.ico=assets\scanner-icon.ico"
if exist "%ROOT%assets\executor_sha256_blocklist.json" set "DATA_ARG=!DATA_ARG! --include-data-files=..\assets\executor_sha256_blocklist.json=assets\executor_sha256_blocklist.json"

set "MODE_ARGS=--mode=onefile --onefile-no-compression"
set "DIST_FILE=%ROOT%dist-secure\virello-scanner.exe"
if /I "%DNG_STANDALONE%"=="1" (
  echo Standalone folder mode ^(set only when testing AV; default is single EXE^).
  set "MODE_ARGS=--mode=standalone"
  set "DIST_FILE="
)

if not exist "dist-secure" mkdir "dist-secure"

echo [4/5] Compiling single EXE with Nuitka ^(several minutes on first run^)...
pushd "_build_obf"
call "..\.venv\Scripts\python.exe" -m nuitka ^
  !MODE_ARGS! ^
  app.py ^
  --assume-yes-for-downloads ^
  --remove-output ^
  --output-dir=..\dist-secure ^
  --output-filename=virello-scanner.exe ^
  --windows-console-mode=disable ^
  --company-name=Virello ^
  "--product-name=Virello Scanner" ^
  "--file-description=Virello Scanner" ^
  --file-version=1.1.0.0 ^
  --product-version=1.1.0.0 ^
  --enable-plugin=tk-inter ^
  --noinclude-pytest-mode=nofollow ^
  --noinclude-setuptools-mode=nofollow ^
  --include-module=embedded_build_config ^
  --include-module=runtime_config ^
  --nofollow-import-to=yara ^
  --python-flag=no_docstrings ^
  %ICON_ARG% %DATA_ARG%
set "BUILD_ERR=!errorlevel!"
popd
if !BUILD_ERR! neq 0 goto :fail

if /I "%DNG_STANDALONE%"=="1" (
  echo [5/5] Creating portable zip...
  call .venv\Scripts\python.exe scripts\package_release.py
  if errorlevel 1 goto :fail
  goto :maybe_sign
)

echo [5/5] Build finished.
set "SIGN_TARGET=%ROOT%dist-secure\virello-scanner.exe"
goto :maybe_sign

:maybe_sign
if defined DNG_SIGN_PFX if exist "!SIGN_TARGET!" (
  echo Code signing...
  signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /f "%DNG_SIGN_PFX%" /p "%DNG_SIGN_PASSWORD%" "!SIGN_TARGET!"
)

echo.
echo Build complete.
echo.
if /I "%DNG_STANDALONE%"=="1" (
  echo Standalone output: %ROOT%dist-secure\
  echo Zip: %ROOT%dist-secure\virello-scanner-portable.zip
) else (
  echo Send only this file to users:
  echo   %ROOT%dist-secure\virello-scanner.exe
)
echo.
echo Security: native machine code via Nuitka. AV tip: sign with DNG_SIGN_PFX if engines still flag it.
echo.
pause
exit /b 0

:fail
echo.
echo Build failed.
pause
exit /b 1
