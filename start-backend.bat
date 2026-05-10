@echo off
cd /d "%~dp0backend"
echo Starting backend at http://localhost:8000
".venv\Scripts\python.exe" server.py
pause
