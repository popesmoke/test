@echo off
cd /d "%~dp0desktop-client"
echo Starting dngscanner
".venv\Scripts\python.exe" app.py
pause
