@echo off
cd /d "%~dp0"
set PYTHONPATH=%cd%;%PYTHONPATH%

:: Використовуємо Python з локального віртуального середовища
set PYTHON=.\.venv\Scripts\python.exe
%PYTHON% Main.py

pause
