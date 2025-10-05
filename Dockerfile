FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full LLMHive application into the container
# (this makes "llmhive.app.main:app" importable)
COPY src/llmhive /app/llmhive

# Cloud Run listens on port 8080
EXPOSE 8080

# Start the FULL app (with routers), not the tiny root app
CMD ["uvicorn", "llmhive.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
