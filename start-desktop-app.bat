@echo off
cd /d "%~dp0desktop-client"
echo Starting desktop diagnostic client
".venv\Scripts\python.exe" app.py
pause
