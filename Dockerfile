FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full LLMHive application into the image
# NOTE: Your code lives in llmhive/src/llmhive (per your screenshots)
COPY llmhive/src/llmhive /app/llmhive

# Cloud Run listens on 8080
EXPOSE 8080

# Start the FULL app (with routers)
CMD ["uvicorn", "llmhive.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
