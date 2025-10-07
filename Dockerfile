FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full repo (so /app/src exists)
COPY . .

# Make 'src' importable so 'from src.llmhive.app.main import app' works
ENV PYTHONPATH="/app/src"

# Cloud Run default port is 8080
ENV PORT=8080

# Start the FULL app via the root app.py
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", $port]
