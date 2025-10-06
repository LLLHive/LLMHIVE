# Root-level entrypoint that exposes the FULL LLMHive API.
# Your full app is at llmhive/src/llmhive/app/main.py
from llmhive.app.main import app  # exposes 'app' for Uvicorn
