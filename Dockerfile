# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory for the entire container.
WORKDIR /app

# Copy the application code from the repository root
# into a 'src' directory inside the container.
# This creates a clean project structure: /app/src/app, /app/src/config, etc.
COPY app/ ./src/app/
COPY main.py ./src/
COPY models.yaml ./src/
COPY requirements.txt ./src/

# Install the Python dependencies from the requirements file now located at /app/src/requirements.txt
RUN pip install --no-cache-dir -r src/requirements.txt

#
# --- THIS IS THE CRITICAL AND CORRECT CONFIGURATION ---
#
# Set the PYTHONPATH to our new source directory.
# This tells the Python interpreter to look for modules inside /app/src.
ENV PYTHONPATH="/app/src"

# Set the working directory to the source folder for the final command.
WORKDIR /app/src
# --- END OF CRITICAL CONFIGURATION ---

# Command to run the application using Gunicorn.
# Because our WORKDIR and PYTHONPATH are now correctly set to /app/src,
# Gunicorn can correctly find the 'app' package, the 'main' module,
# and the 'app' instance inside it.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} main:app -k uvicorn.workers.UvicornWorker"]
