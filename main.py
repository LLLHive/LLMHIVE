from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def root():
    return {"service": "llmhive-orchestrator", "status": "ok", "commit": os.getenv("COMMIT_SHA", "local")}
