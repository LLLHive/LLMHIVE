# Use Python 3.11
FROM python:3.11-slim

# Create app folder
WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add source
COPY main.py .

# Cloud Run listens on $PORT
ENV PORT=8080
EXPOSE 8080

# Start FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
