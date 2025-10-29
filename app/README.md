# LLMHive Application Architecture

This directory contains the modular architecture for the LLMHive multi-agent LLM orchestration platform.

## Directory Structure

```
app/
├── __init__.py
├── config.py              # Configuration and settings management
├── main.py                # FastAPI application entry point
├── api/                   # API endpoints and routes
│   ├── __init__.py
│   └── endpoints.py       # HTTP endpoint definitions
├── agents/                # LLM agent implementations
│   ├── __init__.py
│   ├── base.py            # Abstract base class for agents
│   ├── critic_agent.py    # Critic/evaluation agent
│   ├── editor_agent.py    # Editing/refinement agent
│   └── researcher_agent.py # Research/information gathering agent
├── core/                  # Core utilities and validators
│   ├── __init__.py
│   └── validators.py      # Safety and quality validators
├── memory/                # Memory and knowledge management
│   ├── __init__.py
│   ├── conversation_memory.py  # Short-term conversation history
│   └── knowledge_store.py      # Long-term knowledge storage
├── models/                # Model management and providers
│   ├── __init__.py
│   ├── llm_provider.py    # LLM API provider interfaces
│   └── model_pool.py      # Model catalog and selection
├── orchestration/         # Orchestration engine
│   ├── __init__.py
│   ├── orchestrator.py    # Main orchestration logic
│   ├── planner.py         # Task planning and decomposition
│   ├── router.py          # Dynamic model selection
│   └── synthesizer.py     # Result aggregation and synthesis
└── utils/                 # Utility functions
    └── __init__.py
```

## Key Components

### Orchestration Engine
The brain of the platform that coordinates the entire workflow:
- **Orchestrator**: Main controller managing the full pipeline
- **Planner**: Analyzes prompts and creates execution plans
- **Router**: Selects the best models ("dream team") for each task
- **Synthesizer**: Combines outputs from multiple agents

### Agent System
Specialized LLM agents for different roles:
- **Base Agent**: Abstract interface for all agents
- **Researcher Agent**: Gathers information and supporting data
- **Critic Agent**: Evaluates and critiques outputs
- **Editor Agent**: Refines and polishes final responses

### Model Management
Manages available LLM models:
- **Model Pool**: Catalog of available models with profiles
- **LLM Provider**: Abstract interfaces for different API providers (OpenAI, Anthropic, Google)

### Memory System
Manages conversation context and user knowledge:
- **Conversation Memory**: Short-term dialogue history
- **Knowledge Store**: Long-term user-specific knowledge (vector database integration ready)

### Core Utilities
Safety and quality assurance:
- **Validators**: PII detection, content policy checks, fact verification

## Usage

### Running the Application

```bash
# Recommended: use the helper script from the repo root
./scripts/run_backend.sh

# Using uvicorn directly
python3 -m uvicorn app.app:app --host 0.0.0.0 --port 8080

# Or with the application file at root
python app.py
```

> **Tip:** `scripts/run_backend.sh` automatically activates `.venv` (if present),
> exports `PYTHONPATH` so the `app` package can be imported, and finally launches
> Uvicorn. This removes the need to manage those steps manually on macOS.

### API Endpoints

- `GET /` - Health check
- `POST /api/prompt` - Submit a prompt for processing

### Example API Request

```python
import requests

response = requests.post("http://localhost:8000/api/prompt", json={
    "user_id": "user123",
    "prompt": "Explain quantum computing"
})

print(response.json()["answer"])
```

### Example Direct Usage

```python
from app.orchestration.orchestrator import Orchestrator
import asyncio

async def main():
    orchestrator = Orchestrator(user_id="user123")
    result = await orchestrator.run("Explain quantum computing")
    print(result)

asyncio.run(main())
```

## Configuration

Configuration is managed through `app/config.py` using Pydantic settings. Set environment variables or create a `.env` file:

```env
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
DATABASE_URL=sqlite:///./llmhive.db
```

## Dependencies

See `requirements.txt` for the full list. Key dependencies:
- FastAPI: Web framework
- Pydantic: Data validation and settings
- Uvicorn: ASGI server
- OpenAI/Anthropic/Google client libraries

## Development

All modules include stub implementations ready for production integration with actual LLM APIs.
