variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run"
  type        = string
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
}

variable "image_repository" {
  description = "Artifact Registry repository name"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
}

variable "ingress_hostname" {
  description = "Custom domain to map to the Cloud Run service"
  type        = string
}

variable "vpc_connector_name" {
  description = "Name of the VPC connector for Cloud Run"
  type        = string
}

variable "db_user" {
  description = "Database user"
  type        = string
}

variable "db_pass" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "Database name"
  type        = string
}

variable "cloudsql_private_ip" {
  description = "Private IP of the Cloud SQL instance"
  type        = string
}
