FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.5.1

WORKDIR /app

COPY Programing/pyproject.toml Programing/README.md ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir poetry==${POETRY_VERSION} \
    && poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi \
    && rm -rf ~/.cache/pip

COPY Programing/app ./app
COPY Programing/alembic ./alembic
COPY Programing/alembic.ini ./alembic.ini

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
