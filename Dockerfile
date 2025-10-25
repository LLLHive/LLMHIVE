# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PORT=8080

# 3. Set the working directory in the container
WORKDIR /app

# 4. Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the application code into the container
# This is the corrected step: It copies the 'app' directory
COPY ./app /app

# 6. Make the entrypoint script executable
COPY docker-entrypoint.sh .
RUN chmod +x /app/docker-entrypoint.sh

# 7. Set the entrypoint for the container
ENTRYPOINT ["/app/docker-entrypoint.sh"]
