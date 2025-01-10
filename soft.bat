@echo off
cd /d "%~dp0"
set PYTHONPATH=%cd%;%PYTHONPATH%

set PYTHON=.\.venv\Scripts\python.exe
%PYTHON% Main.py

pause
