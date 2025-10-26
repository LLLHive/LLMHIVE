# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Allow statements and log messages to be sent straight to the logs
# without being buffered.
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container to /app
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend application code into the container at /app
COPY ./app ./app
COPY main.py .

# Expose the port the app runs on. This is for documentation; Cloud Run uses the PORT env var.
EXPOSE 8080

# Command to run the application using Gunicorn.
# This is the final, correct implementation.
# It uses the shell form (`sh -c`) to allow the use of the $PORT environment variable,
# which is the standard and most robust way to run a web service on Cloud Run.
CMD exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 4 --worker-class uvicorn.workers.UvicornWorker main:app
