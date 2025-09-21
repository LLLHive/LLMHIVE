terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.84"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 4.84"
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
  image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.image_repository}/llmhive_fastapi:${var.image_tag}"
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

  metadata {
    annotations = {
      "run.googleapis.com/service-account" = google_service_account.llmhive_runner.email
    }
  }

  template {
    spec {
      service_account_name = google_service_account.llmhive_runner.email

      containers {
        image = local.image

        ports {
          container_port = 8000
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = var.database_secret_name
              version = var.database_secret_version
            }
          }
        }
      }

      vpc_access {
        connector = var.vpc_connector_name
        egress    = "ALL_TRAFFIC"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "public_invoker" {
  service  = google_cloud_run_service.llmhive.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_domain_mapping" "custom_domain" {
  provider = google-beta

  location = var.region
  name     = var.ingress_hostname

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_service.llmhive.name
  }
}
