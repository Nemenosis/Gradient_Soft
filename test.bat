@echo off
REM Активируем виртуальное окружение
call .venv\Scripts\activate

REM Запускаем основной файл проекта
python Main.py
pause