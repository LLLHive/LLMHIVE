# Use official Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables including critical PORT variable
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path to include the application
ENV PYTHONPATH=/app

# Command to run the application - CRITICAL FIX FOR CLOUD RUN
# This ensures the container binds to the PORT environment variable
CMD exec gunicorn --bind :$PORT \
    --workers 1 \
    --threads 8 \
    --timeout 0 \
    "src.llmhive.app.main:app"
