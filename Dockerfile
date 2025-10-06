FROM python:3.11-slim

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ONLY the real LLMHive package into the image
# Your full app is at: llmhive/src/llmhive/app/main.py
COPY llmhive/src/llmhive /app/llmhive

# Make imports & logs reliable
ENV PYTHONUNBUFFERED=1 PYTHONPATH="/app"

# Cloud Run exposes $PORT; default to 8080 locally/dev
EXPOSE 8080
CMD ["sh","-c","python -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
