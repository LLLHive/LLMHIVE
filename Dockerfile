# Use a lightweight Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency list and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full application package into the image
# (This folder contains your FastAPI app at src/llmhive/app/main.py)
COPY src/llmhive /app/llmhive

# Cloud Run listens on port 8080
EXPOSE 8080

# Start the full LLMHive app (NOT the tiny root-only app)
CMD ["uvicorn", "llmhive.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
