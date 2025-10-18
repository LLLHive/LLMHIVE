# ---------- Dockerfile (ROOT of repo) ----------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) Install base Python deps first (better layer caching)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 2) Copy the llmhive package and install it
#    (your pyproject.toml and source live under llmhive/)
COPY llmhive/pyproject.toml llmhive/pyproject.toml
COPY llmhive/src llmhive/src
# optional but harmless:
COPY llmhive/alembic llmhive/alembic
COPY llmhive/alembic.ini llmhive/alembic.ini
COPY llmhive/README.md llmhive/README.md
RUN pip install --no-cache-dir ./llmhive

# 3) Ensure Python can resolve both repo root and src layout at runtime
ENV PYTHONPATH=/app:/app/llmhive:/app/llmhive/src

EXPOSE 8080

# 4) Start the FastAPI app on the Cloud Run port
CMD ["sh","-c","uvicorn llmhive.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
