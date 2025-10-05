FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy full app from llmhive/src/llmhive into container
COPY llmhive/src/llmhive /app/llmhive

# Cloud Run port
EXPOSE 8080

# Start orchestrator API (the real LLMHive app)
CMD ["uvicorn", "llmhive.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
