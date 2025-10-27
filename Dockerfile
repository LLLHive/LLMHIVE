# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set the PYTHONPATH environment variable.
# This tells the Python interpreter to look for modules in the /app directory,
# which is crucial for making our absolute imports work correctly.
ENV PYTHONPATH=/app

# Ensure Python output is sent straight to logs without buffering
ENV PYTHONUNBUFFERED=1

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY ./app ./app
COPY main.py .

# Command to run the application using Gunicorn.
# This uses the shell form to dynamically use the $PORT environment variable
# provided by Cloud Run, which is the most robust method.
CMD exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 4 --worker-class uvicorn.workers.UvicornWorker main:app
