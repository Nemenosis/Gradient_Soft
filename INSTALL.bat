@echo off
REM Убедитесь, что вы находитесь в правильной директории
cd /d "%~dp0"

REM Устанавливаем виртуальное окружение
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Активируем виртуальное окружение
call .venv\Scripts\activate

REM Устанавливаем зависимости
if exist requirements.txt (
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    echo requirements.txt not found!
    exit /b 1
)

pause
