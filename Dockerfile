FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole repo so src/ is available
COPY . .

# Cloud Run port
EXPOSE 8080

# Run the correct FastAPI app path
CMD ["uvicorn", "src.llmhive.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
