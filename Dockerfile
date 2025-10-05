FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the real app package into the image
# (your repo shows the full app lives at: llmhive/src/llmhive/app/main.py)
COPY llmhive/src/llmhive /app/llmhive

# Make logs flush immediately (helps debugging Cloud Run start)
ENV PYTHONUNBUFFERED=1

# Cloud Run will set $PORT; default to 8080 if missing (local/dev)
EXPOSE 8080
CMD ["sh","-c","uvicorn llmhive.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
