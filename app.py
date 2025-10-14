import os, sys
# Ensure our package is importable so Uvicorn can find it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "llmhive", "src"))
from llmhive.app.main import app
