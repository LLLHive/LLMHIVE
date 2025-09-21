variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region"
}

variable "service_name" {
  type        = string
  description = "Cloud Run service name"
}

variable "image_repository" {
  type        = string
  description = "Artifact Registry repository name"
}

variable "image_tag" {
  type        = string
  description = "Container image tag"
}

variable "ingress_hostname" {
  type        = string
  description = "Custom domain for Cloud Run"
}

variable "vpc_connector_name" {
  type        = string
  description = "Serverless VPC connector name"
}

variable "db_user" {
  type        = string
  description = "Database user for the Cloud SQL instance"
}

variable "db_pass" {
  type        = string
  description = "Database password for the Cloud SQL instance"
}

variable "db_name" {
  type        = string
  description = "Database name used by the application"
}

variable "cloudsql_private_ip" {
  type        = string
  description = "Private IP address of the Cloud SQL instance"
}

variable "database_secret_name" {
  type        = string
  description = "Secret Manager secret name containing the DATABASE_URL"
  default     = "llmhive_database_url"
}

variable "database_secret_version" {
  type        = string
  description = "Secret Manager version to pull"
  default     = "latest"
}
