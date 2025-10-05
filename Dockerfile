FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire repo so the nested app is included
COPY . .

# Make Python see the full app regardless of nesting: llmhive/src/llmhive/...
# (your tree shows the app at: llmhive/src/llmhive/app/main.py)
ENV PYTHONPATH="/app/llmhive/src:/app"

# Cloud Run port
EXPOSE 8080

# Start the FULL app (with routers)
# This imports: llmhive/app/main.py -> app = FastAPI(...)
CMD ["uvicorn", "llmhive.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
