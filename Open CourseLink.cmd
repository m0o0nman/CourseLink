@echo off
setlocal
"%~dp0..\work\venv\Scripts\python.exe" "%~dp0..\work\start_demo.py" %*
if errorlevel 1 pause
