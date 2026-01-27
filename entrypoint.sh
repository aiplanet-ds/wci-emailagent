#!/bin/sh
# Backend entrypoint: run migrations then start the app

echo "Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "Migrations completed successfully."
else
    echo "WARNING: Migrations failed. Starting app anyway."
fi

echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
