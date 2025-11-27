# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY llmhive/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (copy llmhive contents to /app)
COPY llmhive/ ./

# Set Python path to include the application
ENV PYTHONPATH=/app

# Command to run the application
CMD exec gunicorn --bind :$PORT \
    --workers 1 \
    --threads 8 \
    --timeout 0 \
    "src.llmhive.app.main:app" \
    -k uvicorn.workers.UvicornWorker

