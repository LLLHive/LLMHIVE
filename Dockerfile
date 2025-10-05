FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ONLY the full LLMHive app package into the image
# (your repo layout shows the app at: llmhive/src/llmhive/app/main.py)
COPY llmhive/src/llmhive /app/llmhive

# Cloud Run listens on 8080
EXPOSE 8080

# Run the FULL app (with routers), not the tiny root app
CMD ["uvicorn", "llmhive.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
