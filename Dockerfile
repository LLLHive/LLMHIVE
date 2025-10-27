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
# This creates the structure: /app/app, /app/config.py, /app/main.py, etc.
COPY app/ ./app/
COPY config.py .
COPY main.py .
COPY models.yaml .

#
# --- THIS IS THE CRITICAL AND CORRECT CONFIGURATION ---
#
# Set the PYTHONPATH environment variable to the working directory's root (/app).
# This tells the Python interpreter to look for modules starting from this directory.
# It allows absolute imports like 'from app.config import settings' and 'from app.app'
# to work correctly from anywhere in the codebase.
ENV PYTHONPATH="${PYTHONPATH}:/app"
# --- END OF CRITICAL CONFIGURATION ---

# Command to run the application using Gunicorn.
# It binds to the port provided by the Cloud Run environment variable.
# The path 'main:app' is correct because main.py is at /app/main.py,
# and it imports the 'app' instance from 'app.app' module.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} main:app -k uvicorn.workers.UvicornWorker"]
