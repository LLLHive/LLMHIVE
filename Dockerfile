# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory, which will be the root for all subsequent operations.
WORKDIR /app

# Copy the requirements file from the repository root into the container's root.
COPY requirements.txt .

# Install the Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application source code from the repository root
# into the container's root working directory (/app).
# This creates the structure: /app/app, /app/main.py, /app/models.yaml, etc.
COPY app/ ./app/
COPY main.py .
COPY models.yaml .

# Validate that critical files exist (fail fast if Dockerfile is misconfigured)
RUN test -f /app/main.py || (echo "ERROR: main.py not found in /app" && exit 1)
RUN test -f /app/app/app.py || (echo "ERROR: app/app.py not found in /app" && exit 1)
RUN test -f /app/requirements.txt || (echo "ERROR: requirements.txt not found in /app" && exit 1)

# Set the PYTHONPATH environment variable to the working directory's root (/app).
# This tells the Python interpreter to look for modules starting from this directory.
# It allows absolute imports like 'from app.config import settings' to work correctly.
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Set the PORT environment variable for Cloud Run (default to 8080 if not set)
ENV PORT=8080

# Command to run the application using Gunicorn with Uvicorn workers.
# This is the ONLY supported entry point.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} main:app -k uvicorn.workers.UvicornWorker"]
