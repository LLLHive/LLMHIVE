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

# Copy only the app code into the container
COPY llmhive/src/llmhive /app/llmhive

# Copy entrypoint script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Make sure Python can find the llmhive package
ENV PYTHONPATH=/app

# Expose the port Cloud Run expects
EXPOSE 8080

# Start the FastAPI app; Cloud Run sets PORT
ENTRYPOINT ["/app/docker-entrypoint.sh"]
