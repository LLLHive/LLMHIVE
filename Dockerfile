FROM python:3.11-slim

# Python run-time settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

# Set working directory inside the container
WORKDIR /app

# Install Python requirements
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the application source tree and make sure Python can import it
COPY llmhive/src/llmhive /app/llmhive
ENV PYTHONPATH=/app

# Expose the port Cloud Run expects
EXPOSE 8080

# Start the FastAPI app; Cloud Run sets PORT
CMD ["/bin/sh", "-c", "uvicorn llmhive.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
