# Use lightweight Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency file and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . .

# Tell Python where to find src folder
ENV PYTHONPATH="/app/src"

# Cloud Run expects the app to listen on PORT (default 8080)
ENV PORT=8080

# Run the full LLMHive FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
