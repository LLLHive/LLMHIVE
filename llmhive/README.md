# LLMHive v3

LLMHive is an AI orchestration platform that coordinates a hive of large language models (LLMs) to
produce richer, more accurate answers than any individual model. Each request progresses through
four phases—independent generation, cross-critique, iterative improvement, and final synthesis—so
the team of models can challenge and elevate one another before delivering a final answer.

The v3 release focuses on a production-ready FastAPI service, database persistence, and complete
deployment tooling for Google Cloud Run and GKE Autopilot.

## Features

- **Multi-model collaboration.** Models generate initial answers, critique peers, refine their
  answers, and synthesize a final response.
- **Async orchestration.** Model calls run concurrently and gracefully handle failures.
- **Database logging.** Every orchestration request is stored in Postgres (or SQLite locally).
- **Extensible providers.** Built-in OpenAI integration with deterministic stubs for development.
- **Container-first deployment.** Dockerfile, Docker Compose, Helm chart, and Terraform for Cloud
  Run ship with the project.

## Repository layout

```
llmhive/
├── src/llmhive/app/      # FastAPI application
│   ├── api/              # Versioned API routers
│   ├── orchestrator.py   # Multi-stage orchestration logic
│   ├── services/         # LLM provider implementations
│   └── ...
├── alembic/              # Database migrations
├── deploy/
│   ├── cloudrun/         # Terraform IaC for Cloud Run
│   └── helm/             # Helm chart for GKE Autopilot
├── docker-compose.yml    # Local dev environment
├── Dockerfile            # Production container image
├── pyproject.toml        # Python project metadata
└── README.md             # This document
```

---
<!-- Trigger Cloud Build -->
## 1. Local development

### 1.1 Prerequisites

- Python 3.11+
- Optional: Docker / Docker Compose
- Optional: PostgreSQL (SQLite is default for local dev)

### 1.2 Setup (virtual environment)

```bash
cd llmhive
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env  # update values as needed
alembic upgrade head  # creates the tasks table
uvicorn llmhive.app.main:app --reload --host 0.0.0.0 --port 8080
```

The API is available at <http://localhost:8080>. Interactive docs live at `/docs` and `/redoc`.

> **Tip:** Without an `OPENAI_API_KEY` the orchestrator automatically uses the bundled stub provider.
> The workflow still executes end-to-end but returns synthetic answers.

### 1.3 Running the tests

```bash
pytest
```

---

## 2. Database migrations

Alembic manages schema migrations. The repository already includes an initial migration that
creates the `tasks` table. To generate additional migrations:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Alembic reads the database URL from `.env` or the `DATABASE_URL` environment variable. For local
development the default SQLite database (`sqlite:///./llmhive.db`) is automatically created.

---

## 3. Docker & Docker Compose

### 3.1 Build the image

```bash
cd llmhive
docker build -t ghcr.io/your-org/llmhive:latest .
```

### 3.2 Run locally with Docker

```bash
docker run --rm -p 8080:8080 \
  -e DATABASE_URL=sqlite:////data/llmhive.db \
  -v $(pwd)/data:/data \
  ghcr.io/your-org/llmhive:latest
```

### 3.3 Docker Compose

`docker-compose.yml` includes services for the API and PostgreSQL. Update `.env` with a Postgres
URL before running:

```bash
cp .env.example .env
# Edit DATABASE_URL to match the docker-compose Postgres credentials
docker-compose up --build
```

FastAPI listens on <http://localhost:8080> and Postgres is exposed on `localhost:5433`.

---

## 4. Google Cloud deployments

LLMHive ships with two official deployment targets. Both require the container image to be pushed to
Google Artifact Registry (GAR) or Container Registry (GCR).

### 4.1 Build and push the image

```bash
PROJECT_ID="your-gcp-project"
REGION="us-central1"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/llmhive/llmhive:latest"

gcloud auth login
gcloud config set project "$PROJECT_ID"
gcloud auth configure-docker "${REGION}-docker.pkg.dev"
docker build -t "$IMAGE" .
docker push "$IMAGE"
```

---

### 4.2 Deploy to GKE Autopilot with Helm

#### Prerequisites

1. A GKE Autopilot cluster with the [External Secrets Operator](https://external-secrets.io/) installed.
2. Workload Identity configured on the cluster.
3. A Google Secret Manager (GSM) secret containing the database URL.
4. A Google service account (GSA) with `roles/secretmanager.secretAccessor` on the secret.

#### One-time setup

```bash
# Create the secret in Google Secret Manager
DB_URL="postgresql+psycopg://user:pass@host:5432/llmhive"
PROJECT_ID="your-gcp-project"
SECRET_NAME="llmhive-database-url"

gcloud secrets create "$SECRET_NAME" --replication-policy="automatic"
printf "%s" "$DB_URL" | gcloud secrets versions add "$SECRET_NAME" --data-file=-

# Create a Google service account for the workload identity binding
GSA="llmhive-gsa"
gcloud iam service-accounts create "$GSA"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${GSA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### Helm deployment

1. Update `deploy/helm/llmhive/values-prod.yaml` with your image, domain, and secret details.
2. Install or upgrade the release:

```bash
helm upgrade --install llmhive deploy/helm/llmhive \
  --values deploy/helm/llmhive/values-prod.yaml \
  --set image.repository="${REGION}-docker.pkg.dev/${PROJECT_ID}/llmhive/llmhive" \
  --set image.tag="latest"
```

#### Verification

```bash
kubectl get pods
kubectl describe externalsecret llmhive-secrets
kubectl get ingress
```

Once the ingress shows an address, map the DNS record for your domain to the provided IP. If using
Google-managed certificates, the Ingress automatically provisions TLS once DNS resolves correctly.

---

### 4.3 Deploy to Cloud Run with Terraform

The Terraform module in `deploy/cloudrun/terraform/` provisions a Cloud Run service, VPC connector,
and optional custom domain mapping.

#### Configure variables

1. Copy the example tfvars file:

```bash
cd deploy/cloudrun/terraform
cp env.example.auto.tfvars env.auto.tfvars
```

2. Edit `env.auto.tfvars` to set:
   - `project` – GCP project ID
   - `region` – Cloud Run region (e.g., `us-central1`)
   - `image` – GAR/GCR image reference
   - `database_secret` – Name of the GSM secret with your database URL
   - `service_account_email` – Service account for Cloud Run (needs Secret Manager access)
   - Optional: `domain` for custom domain mapping

#### Apply Terraform

```bash
terraform init
terraform plan
terraform apply
```

#### Post-deploy

- The `service_url` output contains the deployed HTTPS endpoint.
- If `domain` was provided, update DNS to point the domain to Cloud Run per the Terraform output.
- Monitor logs with `gcloud logs tail --project $PROJECT_ID --service=llmhive`.

---

## 5. Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `ProviderNotConfiguredError` in logs | Ensure `OPENAI_API_KEY` is set, or rely on the stub provider for testing. |
| ExternalSecret stuck in `Error` | Confirm the External Secrets Operator is installed and the Workload Identity binding has `secretAccessor`. |
| Cloud Run fails to deploy | Verify the container image exists in the registry and the service account has `roles/run.admin` and `roles/secretmanager.secretAccessor`. |
| Database errors locally | Remove `llmhive.db` and rerun `alembic upgrade head`. |

---

## 6. API reference

- `GET /api/v1/healthz` – health probe
- `POST /api/v1/orchestration/` – run the orchestration workflow

Example request:

```json
{
  "prompt": "Summarize the history of renewable energy policies.",
  "models": ["gpt-4o-mini", "gpt-3.5-turbo"]
}
```

Example response fields:

- `initial_responses` – independent answers from each model
- `critiques` – cross-evaluations where models challenge each other
- `improvements` – refined answers after receiving critiques
- `final_response` – synthesized response returned to the user

---

## 7. Extending LLMHive

1. Implement a new provider class that satisfies `LLMProvider` (see `app/services/base.py`).
2. Register it in `Orchestrator._default_providers` or pass in a provider map when instantiating.
3. Update deployment secrets to include the new provider credentials.

---

## 8. Support

For issues or feature requests, open a GitHub issue with detailed reproduction steps. Pull requests
are welcome—please include tests and documentation updates.
