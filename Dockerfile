# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory for the container
WORKDIR /app

# Copy dependency manifests first to leverage Docker layer caching
COPY requirements.txt ./
COPY llmhive/requirements.txt ./llmhive/requirements.txt

# Install runtime dependencies for both the legacy app/ runtime and the
# refactored llmhive/src package.  Keeping the installs separate makes the
# layer cache friendlier when only one requirements file changes.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r llmhive/requirements.txt

# Copy the application code into the image
COPY . .

# Ensure both the repository root (legacy layout) and the new
# llmhive/src package directory are on the Python path.
ENV PYTHONPATH="/app:/app/llmhive/src"

# Expose the FastAPI app via Gunicorn/Uvicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} main:app -k uvicorn.workers.UvicornWorker"]
