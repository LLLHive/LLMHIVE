# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container.
# Note: We are copying from the llmhive subdirectory.
COPY llmhive/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code into the container.
# This copies the contents of the llmhive/src/llmhive directory into /app.
COPY llmhive/src/llmhive/ .

# Set the PYTHONPATH to include the application's root directory.
# This is the CRITICAL FIX that allows imports like 'from config' to work.
ENV PYTHONPATH=/app:${PYTHONPATH}

# Command to run the application using Gunicorn.
# 'app.main:app' correctly points to the 'app' instance in the 'app/main.py' file.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} app.main:app -k uvicorn.workers.UvicornWorker"]
