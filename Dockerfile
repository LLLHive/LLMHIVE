# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code into the container at /app
COPY . .

# Set the PYTHONPATH to include the /app directory
# This ensures that Python can find modules like 'config' and 'app' directly
ENV PYTHONPATH=/app

# Command to run the application using Gunicorn with Uvicorn workers
# It binds to 0.0.0.0 and uses the PORT environment variable provided by Cloud Run
# 'main:app' uses our main.py which imports the FastAPI instance
CMD exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 4 --worker-class uvicorn.workers.UvicornWorker main:app
