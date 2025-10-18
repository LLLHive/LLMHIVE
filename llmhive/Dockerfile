FROM python:3.11-slim

ENV PYTHONPATH=/app:/app/llmhive:/app/llmhive/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# Install all dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application code, alembic files and env example
COPY src/llmhive ./src/llmhive
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY README.md ./README.md
COPY .env.example ./

# Install llmhive as a package
RUN pip install .

EXPOSE 8080

# Start the FastAPI app via uvicorn
CMD ["sh","-c","uvicorn llmhive.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
