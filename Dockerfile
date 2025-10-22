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

# Copy the packaged source tree and install it so imports work without a custom
# PYTHONPATH. Installing the package avoids runtime import errors even if
# deployment-time environment variables overwrite the image defaults.
COPY llmhive /opt/llmhive
RUN pip install --no-cache-dir /opt/llmhive --no-deps && rm -rf /opt/llmhive

# Expose the port Cloud Run expects
EXPOSE 8080

# Start the FastAPI app; Cloud Run sets PORT
CMD ["/bin/sh", "-c", "uvicorn llmhive.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
