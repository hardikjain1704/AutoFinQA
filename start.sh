#!/bin/bash

echo "Starting Nginx..."
nginx

echo "Starting FastAPI backend..."
cd /app
uvicorn auto_finQA.router.main:app --host 0.0.0.0 --port 8000 &

echo "Application started successfully!"
echo "Frontend: http://localhost:7860"
echo "Backend API: http://localhost:8000"

wait
