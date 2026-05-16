@echo off
cd /d "%~dp0desktop-client"
echo Starting Virello Scanner
".venv\Scripts\python.exe" app.py
pause
