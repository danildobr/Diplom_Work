# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект внутрь контейнера
COPY . .

# EXPOSE порт, на котором будет работать Django
EXPOSE 8000

# Команда для запуска приложения
CMD ["gunicorn", "My_first_store.wsgi:application", "--bind", "0.0.0.0:8000"]