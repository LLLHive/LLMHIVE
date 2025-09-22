# LLMHIVE Orchestrator

LLMHIVE is a multi-LLM orchestration platform that decomposes complex user queries
into optimized workflows spanning multiple expert models. The service exposes a
FastAPI endpoint that performs prompt optimization, model routing, ensemble
execution, adversarial debate, fact-checking, and consensus synthesis while
keeping internal reasoning private.

## Architecture

```
+-------------+      +-----------------+      +-----------------+
|  FastAPI    | ---> | Prompt Optimizer| ---> | Router / Equal. |
+-------------+      +-----------------+      +-----------------+
        |                        |                         |
        v                        v                         v
+-------------+      +-----------------+      +-----------------+
| Ensemble    | ---> | Voting & Debate | ---> | Fact Checkers   |
+-------------+      +-----------------+      +-----------------+
        |                                                 |
        +----------------------> Consensus Builder <------+
                                 |        |
                                 v        v
                            Incognito   Memory
```

* **Prompt Optimization** refines the user query, splits it into segments, and
  generates complementary prompt variants.
* **Equalizer** maps user sliders (accuracy, speed, creativity, cost) into an
  orchestration profile that drives routing depth, sample counts, challenge
  rounds, and fact-checking.
* **Router** weighs model scorecards and historical performance to select the
  best adapters. Adapters include OpenAI, Anthropic, Google, Azure, and a local
  OSS stub for development.
* **Ensemble Runner** executes the selected models asynchronously, recording
  latency, cost, and quality heuristics.
* **Voting, Challenge, and Fact-Checking** provide internal critique loops that
  stay private. Feature flags toggle debate and verification without code
  changes.
* **Consensus Builder** synthesizes the winning answer, normalizes tone using
  incognito style redaction, and calculates a confidence score.
* **Memory Store** keeps interaction history and model scorecards to improve
  routing over time.

## Getting Started

### Prerequisites

* Python 3.11+
* Optional: Docker / Docker Compose

### Local development

```bash
cd llmhive
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn llmhive.app.main:app --host 0.0.0.0 --port 8080 --reload
```

Open http://localhost:8080/docs for interactive documentation.

### Docker Compose

```bash
cd llmhive
docker-compose up --build
```

This starts the API alongside a Postgres container. The API still defaults to
SQLite unless you change `DB_URL` in `.env` or the compose file.

### Cloud Run

The included `cloudrun.yaml` documents deployment parameters. Build the container
and deploy via `gcloud run deploy` using the image built from the provided
Dockerfile. Ensure environment variables for provider keys are set securely.

## Configuration

Runtime settings live in `app/core/settings.py` and can be overridden via a
`.env` file or environment variables. Key options include:

* `DB_URL` – SQLite for development, Postgres for production.
* `ENABLE_DEBATE` and `ENABLE_FACTCHECK` – toggle internal critique loops.
* Provider API keys – adapters gracefully degrade when credentials are absent.

## API

* `POST /api/v1/orchestrate` – main orchestration endpoint.
* `GET /health` – readiness check.
* `GET /docs` – Swagger UI provided by FastAPI.

Example request:

```json
{
  "query": "Summarize recent advances in battery technology",
  "options": {"accuracy": 0.8, "speed": 0.4, "creativity": 0.3, "cost": 0.5}
}
```

## Testing

```bash
cd llmhive
pytest
```

Coverage configuration lives in `pyproject.toml`. The test suite validates the
API contract, orchestrator pipeline, prompt optimizer, and consensus synthesis.

## Extending LLMHIVE

### Adding a new adapter

1. Create a new file in `app/orchestration/adapters/` implementing
   `BaseLLMAdapter`.
2. Register the adapter inside `AdapterRegistry`.
3. Update environment variables or secrets to provide credentials.

### Equalizer slider mapping

The dynamic criteria equalizer maps sliders to orchestration profiles:

* Higher **accuracy** increases the number of models, samples, and enables
  fact-checking.
* Higher **speed** reduces sampling depth and disables debate.
* Higher **creativity** increases prompt variant generation and sampling
  temperature.
* Lower **cost** constrains model count and disables verification loops.

Adjust `app/orchestration/equalizer.py` to refine these mappings as new models or
strategies become available.

## Database Migrations

An Alembic scaffold is provided. Initialize migrations by running:

```bash
alembic init app/db/alembic
```

Then generate and upgrade migrations as needed. The `init_db` helper creates
SQLite tables for local experimentation.

## Observability

Structured JSON logging is enabled via `app/core/logging.py`. Integrate with
OpenTelemetry by instrumenting the FastAPI application or individual adapters.

## Security

* Internal critiques, tool traces, and provider identifiers are never exposed in
  API responses.
* `utils/redact.py` normalizes tone and removes simple PII patterns before
  returning results.
* Fact-checking restricts outbound calls to an allowlist defined in settings.

## Makefile Targets

* `make dev` – create a virtual environment and install dev dependencies.
* `make test` – run the pytest suite.
* `make run-local` – start the FastAPI app with reload enabled.
* `make migrate` – run Alembic migrations (requires prior configuration).

## License

This project is provided as-is for demonstration purposes. Customize and secure
it before deploying to production.
