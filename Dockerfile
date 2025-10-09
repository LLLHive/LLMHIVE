# Use an official Python image as the base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install any necessary dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into the image
COPY . .

# Expose the default port (Cloud Run uses 8080 by default)
EXPOSE 8080

# Start the FastAPI app with Uvicorn, binding to 0.0.0.0 and using the Cloud Run PORT env variable
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "${PORT:-8080}"]
