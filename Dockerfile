# Use a lightweight Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy dependency files first
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code
COPY . .

# Expose the Cloud Run port
EXPOSE 8080

# Start the full orchestrator app
CMD ["uvicorn", "src.llmhive.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
