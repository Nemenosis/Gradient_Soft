@echo off
echo --- Проверяем наличие Python ---
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ОШИБКА]: Python не установлен! Установите Python и добавьте его в PATH.
    pause
    exit /b 1
)

echo --- Создаем виртуальное окружение ---
IF NOT EXIST venv (
    python -m venv venv
    echo Виртуальное окружение создано.
) ELSE (
    echo Виртуальное окружение уже существует.
)

echo --- Активируем виртуальное окружение ---
call venv\Scripts\activate

echo --- Устанавливаем зависимости ---
pip install --upgrade pip
pip install -r requirements.txt

IF ERRORLEVEL 1 (
    echo [ОШИБКА]: Не удалось установить зависимости!
    pause
    exit /b 1
)
echo Зависимости успешно установлены.
deactivate
pause
