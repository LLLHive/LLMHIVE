FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY README.md ./README.md
COPY .env.example ./

RUN pip install .

EXPOSE 8080

CMD ["sh", "-c", "uvicorn llmhive.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
