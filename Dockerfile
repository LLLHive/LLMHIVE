FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full repo (so /app/src/llmhive exists)
COPY . .

# Make 'src' importable so 'from src.llmhive.app.main import app' works
ENV PYTHONPATH="/app/src/llmhive"

# Cloud Run default port is 8080
ENV PORT=8080

cmd unicorn main.app
import uvicorn
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
