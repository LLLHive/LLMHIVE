# Simple robust Dockerfile for Cloud Run + Python FastAPI app
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# System packages required for some wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt \
 && pip install --no-cache-dir gunicorn uvicorn

# Copy application source to a predictable path Python can import
COPY llmhive/src/llmhive /app/llmhive

# Ensure /app is on PYTHONPATH so package imports work
ENV PYTHONPATH=/app

# Copy start script that launches gunicorn + uvicorn worker
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8080

# Use the start script so we control binding and print simple env diagnostics
CMD ["/app/start.sh"]
