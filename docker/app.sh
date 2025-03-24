#!/bin/bash

# Выполнение миграций с Alembic
alembic upgrade head

# Переход в каталог с приложением (если нужно)
cd /fastapi_app

# Запуск Gunicorn с FastAPI через Uvicorn Worker
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000
