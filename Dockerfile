FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (leverages Docker layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code into the image
COPY . .

# Ensure Python can resolve our package layout
ENV PYTHONPATH=/app:/app/llmhive:/app/llmhive/src

# Start Uvicorn on the port Cloud Run provides (default 8080)
CMD ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
