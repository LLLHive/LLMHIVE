# Use a lightweight Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency files first
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . .

# Expose the port used by Cloud Run
EXPOSE 8080

# Run the orchestrator entry point
CMD ["uvicorn", "src.llmhive.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
