# Используем официальный образ Python
FROM python:3.12-slim

# Отключаем кеширование pyc-файлов и буферизацию вывода
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию
WORKDIR /gradient

# Копируем зависимости
COPY requirements.txt /tmp/requirements.txt

# Устанавливаем зависимости
RUN pip3 install --upgrade pip && \
    pip install \
    --no-cache-dir \
    -r /tmp/requirements.txt

# Копируем проект
COPY . .

# Указываем, что по умолчанию будет запускаться
# Чтение переменной MODE и запуск нужного скрипта
CMD ["sh", "-c", "python main.py --mode $MODE"]
