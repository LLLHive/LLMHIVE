terraform {
  required_version = ">= 1.4.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.10.0"
    }
  }
}

provider "google" {
  project = var.project
  region  = var.region
}

locals {
  vpc_connector_name = var.vpc_create_connector ? google_vpc_access_connector.connector[0].name : var.vpc_connector_name
}

resource "google_vpc_access_connector" "connector" {
  count       = var.vpc_create_connector ? 1 : 0
  name        = var.vpc_connector_name
  region      = var.region
  network     = var.vpc_network
  ip_cidr_range = var.vpc_connector_cidr
}

resource "google_cloud_run_service" "llmhive" {
  name     = var.service_name
  location = var.region

  template {
    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" = local.vpc_connector_name
        "run.googleapis.com/vpc-access-egress"    = var.vpc_egress_settings
        "autoscaling.knative.dev/minScale"        = tostring(var.min_instances)
        "autoscaling.knative.dev/maxScale"        = tostring(var.max_instances)
      }
    }

    spec {
      service_account_name = var.service_account_email
      container_concurrency = var.container_concurrency

      containers {
        image = var.image

        ports {
          name           = "http1"
          container_port = 8080
        }

        env {
          name  = "PORT"
          value = "8080"
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = var.database_secret
              version = var.database_secret_version
            }
          }
        }

        dynamic "env" {
          for_each = var.environment
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = var.secret_environment_variables
          content {
            name = env.value.name
            value_source {
              secret_key_ref {
                secret  = env.value.secret
                version = coalesce(env.value.version, "latest")
              }
            }
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "invoker" {
  count   = var.allow_unauthenticated ? 1 : 0
  service = google_cloud_run_service.llmhive.name
  location = google_cloud_run_service.llmhive.location
  role    = "roles/run.invoker"
  member  = "allUsers"
}

resource "google_cloud_run_domain_mapping" "custom_domain" {
  count   = var.domain == "" ? 0 : 1
  location = var.region
  name     = var.domain
  metadata {
    namespace = var.project
  }
  spec {
    route_name = google_cloud_run_service.llmhive.name
  }
}
