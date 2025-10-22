# Production-ready Dockerfile for deploying LLMHive on Cloud Run
FROM python:3.11-slim

# Ensure logs are flushed immediately and disable Poetry virtualenv creation
ENV PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# Install minimal system dependencies required for building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r /app/requirements.txt \
  && pip install --no-cache-dir gunicorn uvicorn

# Copy the entire application source
COPY . /app

# Ensure the startup script is executable
RUN chmod +x /app/start.sh

# Cloud Run provides PORT at runtime; default to 8080 for local use
ENV PORT=8080
EXPOSE 8080

# Delegate startup to start.sh so Gunicorn binds to the configured PORT
CMD ["/app/start.sh"]
