terraform {
  required_version = ">= 1.3.0"
}

variable "database_secret_name" {
  description = "Secret Manager secret storing the database connection info."
  type        = string
}

variable "database_secret_version" {
  description = "Secret Manager secret version containing the database connection info."
  type        = string
  default     = "latest"
}

locals {
  container_definition = {
    env = [{
      name = "DATABASE_URL"
      value_from = {
        secret_key_ref = {
          name = var.database_secret_name
          key  = var.database_secret_version
        }
      }
    }]
  }
}

output "container_env" {
  description = "Structured representation of the Cloud Run container environment configuration."
  value       = local.container_definition.env
}
