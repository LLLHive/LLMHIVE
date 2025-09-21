terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.74.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 4.74.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

locals {
  image         = "${var.region}-docker.pkg.dev/${var.project_id}/${var.image_repository}/llmhive_fastapi:${var.image_tag}"
  database_url  = "postgresql+psycopg2://${var.db_user}:${var.db_pass}@${var.cloudsql_private_ip}:5432/${var.db_name}"
  secret_id     = "llmhive_database_url"
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = local.secret_id

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = local.database_url
}

resource "google_service_account" "llmhive_runner" {
  account_id   = "llmhive-runner"
  display_name = "LLMHIVE Cloud Run runtime service account"
}

resource "google_project_iam_member" "run_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.llmhive_runner.email}"
}

resource "google_project_iam_member" "run_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.llmhive_runner.email}"
}

resource "google_cloud_run_service" "llmhive" {
  provider = google-beta
  name     = var.service_name
  location = var.region

  template {
    metadata {
      annotations = {
        "run.googleapis.com/service-account" = google_service_account.llmhive_runner.email
        "run.googleapis.com/ingress" = "all"
      }
    }

    spec {
      containers {
        image = local.image

        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = google_secret_manager_secret_version.database_url.version
            }
          }
        }
      }

      vpc_access {
        connector = var.vpc_connector_name
        egress     = "ALL_TRAFFIC"
      }

      container_concurrency = 80
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true
}

resource "google_cloud_run_domain_mapping" "custom_domain" {
  location = var.region
  name     = var.ingress_hostname
  metadata {
    namespace = var.project_id
  }
  spec {
    route_name = google_cloud_run_service.llmhive.name
  }
}

resource "google_cloud_run_service_iam_member" "public_invoker" {
  location = var.region
  project  = var.project_id
  service  = google_cloud_run_service.llmhive.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
