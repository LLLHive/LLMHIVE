# Root-level entrypoint that imports the real FastAPI app.
# Your full app lives at llmhive/src/llmhive/app/main.py
from llmhive.app.main import app  # exposes 'app' for Uvicorn
