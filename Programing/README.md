# LLMHIVE FastAPI Service

This project bundles a lightweight FastAPI application together with all of the
artifacts required to deploy it locally, to Google Kubernetes Engine (GKE)
Autopilot by way of Helm, and to Cloud Run through Terraform automation. The
goal of this repository is to act as a complete reference implementation so
that an environment can be reproduced with minimal guesswork.

## Repository layout

```
Programing/
├── app/                      # FastAPI application package
│   ├── api/                  # Example API router
│   ├── config.py             # Centralised environment configuration
│   ├── database.py           # SQLAlchemy session helpers
│   └── main.py               # FastAPI entrypoint (uvicorn app.main:app)
├── alembic/                  # Database migration environment
│   └── versions/             # Example migration scripts
├── deploy/
│   ├── helm/llmhive/         # Helm chart for the Kubernetes deployment
│   └── cloudrun/terraform/   # Terraform for Cloud Run rollout
├── Dockerfile                # Container build recipe for the app
├── docker-compose.yml        # Local Compose stack with Postgres
├── pyproject.toml            # Project metadata and dependencies
└── README.md                 # This documentation
```

## Key configuration files

The table below explains the deployment files that commonly need adjusting
before a production rollout.

| File | Purpose | Notes |
| ---- | ------- | ----- |
| `Dockerfile` | Builds the service image with FastAPI and Alembic installed. | Exposes port 8000 for uvicorn and copies the migration assets. |
| `docker-compose.yml` | Runs the API alongside a local Postgres instance. | The app receives `DATABASE_URL` pointing at the Compose database and still honours `.env` overrides. |
| `.env.example` | Template for local environment variables. | Defaults to SQLite for quick starts and documents the Postgres connection string used by Compose or Cloud SQL. |
| `deploy/helm/llmhive/values.yaml` | Baseline Helm defaults. | Suitable for local testing against SQLite. |
| `deploy/helm/llmhive/values-prod.yaml` | GKE production overrides. | Supply Artifact Registry coordinates, ingress host, and Workload Identity values here. |
| `deploy/helm/llmhive/templates/external-secret.yaml` | External Secrets Operator manifest. | Pulls the database URL from Google Secret Manager when `useExternalSecret` is enabled. |
| `deploy/helm/llmhive/templates/serviceaccount.yaml` | Workload Identity service account. | Annotates the Kubernetes ServiceAccount with the mapped Google Service Account. |
| `deploy/cloudrun/terraform/main.tf` | Cloud Run infrastructure as code. | Creates the service, binds IAM permissions, attaches a VPC connector, and maps a custom domain. |
| `deploy/cloudrun/terraform/env.example.auto.tfvars` | Terraform variable template. | Copy to `env.auto.tfvars` and fill in project specific values including the secret name containing `DATABASE_URL`. |

## Local development runbook (SQLite or Docker Compose)

### Prerequisites

* Python 3.11+
* Optional: Docker and Docker Compose v2 for container-based workflows

### Steps

1. **Create a virtual environment and install dependencies**

   ```bash
   cd Programing
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -e .
   ```

2. **Configure environment variables**

   ```bash
   cp .env.example .env
   # Optionally switch to Postgres by uncommenting the DATABASE_URL line
   ```

3. **Apply migrations (if the schema changes)**

   ```bash
   alembic upgrade head
   ```

4. **Start the API**

   ```bash
   uvicorn app.main:app --reload
   ```

   The service listens on `http://127.0.0.1:8000`. Visit `/docs` for the
   interactive API explorer or `/healthz` for a simple health probe.

5. **Alternative: run via Docker Compose**

   ```bash
   docker compose up --build
   ```

   Compose will build the application image, start Postgres, and publish the
   API on port 8000 using the Postgres connection string defined in the stack.
   The `.env` file is still honoured so you can layer additional settings.

## GKE Autopilot runbook (Helm + External Secrets)

This path deploys the API to a GKE Autopilot cluster while sourcing the
`DATABASE_URL` from Google Secret Manager through the External Secrets
Operator (ESO).

1. **Ensure cluster access**
   * Provision or reuse an Autopilot cluster (`gcloud container clusters create-auto`).
   * Fetch credentials using `gcloud container clusters get-credentials`.

2. **Build and push the container image**

   ```bash
   docker build -t <REGION>-docker.pkg.dev/<PROJECT_ID>/<AR_REPO>/llmhive_fastapi:<IMAGE_TAG> .
   gcloud auth configure-docker <REGION>-docker.pkg.dev
   docker push <REGION>-docker.pkg.dev/<PROJECT_ID>/<AR_REPO>/llmhive_fastapi:<IMAGE_TAG>
   ```

3. **Prepare Cloud SQL**
   * Create a PostgreSQL instance with a private IP in the same VPC as the cluster.
   * Create the database and application user.

4. **Seed the Secret Manager secret**

   ```bash
   gcloud secrets create llmhive_database_url --replication-policy="automatic"
   echo -n "postgresql+psycopg2://<DB_USER>:<DB_PASS>@<CLOUDSQL_PRIVATE_IP>:5432/<DB_NAME>" \
     | gcloud secrets versions add llmhive_database_url --data-file=-
   ```

5. **Configure Workload Identity**
   * Create a Google Service Account (GSA) such as `llmhive-app-gsa`.
   * Grant it `roles/secretmanager.secretAccessor` and `roles/cloudsql.client`.
   * Bind the Kubernetes ServiceAccount specified in `values-prod.yaml` to the GSA:

     ```bash
     gcloud iam service-accounts add-iam-policy-binding \
       llmhive-app-gsa@<PROJECT_ID>.iam.gserviceaccount.com \
       --role roles/iam.workloadIdentityUser \
       --member "serviceAccount:<PROJECT_ID>.svc.id.goog[<NAMESPACE>/llmhive-app]"
     ```

6. **Install the External Secrets Operator (once per cluster)**

   ```bash
   helm repo add external-secrets https://charts.external-secrets.io
   helm install external-secrets external-secrets/external-secrets \
     --namespace external-secrets --create-namespace
   ```

   Configure a `ClusterSecretStore` named `gsm-store` pointing at your project.

7. **Deploy the chart**

   ```bash
   cd deploy/helm/llmhive
   helm upgrade --install llmhive . \
     --namespace llmhive --create-namespace \
     -f values-prod.yaml \
     --set image.repository=<REGION>-docker.pkg.dev/<PROJECT_ID>/<AR_REPO>/llmhive_fastapi \
     --set image.tag=<IMAGE_TAG> \
     --set ingress.host=LLMHIVE.AI \
     --set externalSecret.gsmSecretName="projects/<PROJECT_ID>/secrets/llmhive_database_url" \
     --set workloadIdentity.ksaName=llmhive-app \
     --set workloadIdentity.gsaEmail=llmhive-app-gsa@<PROJECT_ID>.iam.gserviceaccount.com
   ```

8. **Verify the deployment**
   * `kubectl -n llmhive get pods,svc,ingress,externalsecret`
   * Ensure the ingress address is published and point DNS for `LLMHIVE.AI` to it.
   * Run database migrations against Cloud SQL (`alembic upgrade head` with the
     production `DATABASE_URL`).

## Cloud Run runbook (Terraform)

The Terraform configuration under `deploy/cloudrun/terraform` provisions the
Cloud Run service, attaches a VPC connector, configures IAM, and maps a custom
domain.

1. **Prerequisites**
   * Enable the Cloud Run, Artifact Registry, Secret Manager, Cloud Build,
     Cloud SQL Admin, and VPC Access APIs.
   * Build and push the container image as in the GKE workflow.
   * Create a Serverless VPC connector (for example `llmhive-connector`).
   * Ensure the Secret Manager secret `llmhive_database_url` exists (see the
     command in the GKE runbook).

2. **Configure Terraform variables**

   ```bash
   cd deploy/cloudrun/terraform
   cp env.example.auto.tfvars env.auto.tfvars
   # edit env.auto.tfvars with your project values
   ```

   Required values include the project ID, region, service name, Artifact
   Registry repository/tag, VPC connector name, custom domain, and the
   database credentials/private IP that correspond to your Cloud SQL instance.
   The Terraform module defaults the Secret Manager name to
   `llmhive_database_url`; adjust the variable if your secret is named
   differently.

3. **Initialise and apply**

   ```bash
   terraform init
   terraform apply
   ```

   The module creates a dedicated Cloud Run service account with access to
   Secret Manager and Cloud SQL, deploys the service, attaches the VPC
   connector, and configures public ingress.

4. **Set up the domain mapping**
   * Terraform creates a `google_cloud_run_domain_mapping`. After the apply
     finishes, retrieve the required DNS records via `gcloud run domain-mappings
     describe` and configure them with your DNS provider.
   * Wait for the SSL certificate to become active before relying on the
     endpoint.

5. **Confirm deployment**
   * `gcloud run services describe <SERVICE> --region <REGION>` should report a
     healthy status.
   * `curl -I https://LLMHIVE.AI/healthz` should return a 200 once DNS and TLS
     propagate.

## Final verification checklist

- [ ] `DATABASE_URL` secret exists in Google Secret Manager and contains a valid
      connection string.
- [ ] Alembic migrations have been applied to the target database.
- [ ] Kubernetes pods or Cloud Run revisions report healthy status and can reach
      the database via the configured networking.
- [ ] DNS for `LLMHIVE.AI` points to the GKE ingress IP or Cloud Run domain
      mapping, and TLS certificates show as active.
- [ ] Monitoring and logging (Cloud Logging, Cloud Monitoring) show no startup
      errors or permission denials.

## Troubleshooting tips

| Symptom | Resolution |
| ------- | ---------- |
| ExternalSecret stuck in `ERROR` | Verify the Workload Identity binding and that the `gsm-store` `ClusterSecretStore` references the correct project. |
| Pod fails with database connection errors | Confirm the `app-secrets` secret contains the right connection string and that network peering/VPC access to Cloud SQL is configured. |
| Cloud Run returns 502/504 | Check Cloud Run logs for traceback information and confirm the VPC connector is in the same region and project as the Cloud SQL instance. |
| Custom domain not issuing TLS | Ensure DNS records match the domain mapping output and allow time for certificate provisioning. |

This documentation should provide everything necessary to stand up LLMHIVE in
development or production environments with confidence.
