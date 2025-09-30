variable "project" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "Cloud Run region"
  type        = string
}

variable "image" {
  description = "Container image to deploy"
  type        = string
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "llmhive"
}

variable "service_account_email" {
  description = "Service account email used by Cloud Run"
  type        = string
}

variable "database_secret" {
  description = "Secret Manager secret containing DATABASE_URL"
  type        = string
}

variable "database_secret_version" {
  description = "Version of the database secret"
  type        = string
  default     = "latest"
}

variable "environment" {
  description = "Plaintext environment variables"
  type        = map(string)
  default     = {}
}

variable "secret_environment_variables" {
  description = "Additional secret environment variables"
  type = list(object({
    name    = string
    secret  = string
    version = optional(string)
  }))
  default = []
}

variable "container_concurrency" {
  description = "Maximum concurrent requests per container"
  type        = number
  default     = 80
}

variable "min_instances" {
  description = "Minimum number of serving instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of serving instances"
  type        = number
  default     = 4
}

variable "allow_unauthenticated" {
  description = "Whether to allow public access to the Cloud Run service"
  type        = bool
  default     = true
}

variable "vpc_create_connector" {
  description = "If true, create a new VPC Access Connector"
  type        = bool
  default     = true
}

variable "vpc_connector_name" {
  description = "Name of the VPC Access Connector"
  type        = string
  default     = "llmhive-connector"
}

variable "vpc_network" {
  description = "VPC network name for the connector"
  type        = string
  default     = "default"
}

variable "vpc_connector_cidr" {
  description = "CIDR range allocated to the VPC connector"
  type        = string
  default     = "10.8.0.0/28"
}

variable "vpc_egress_settings" {
  description = "Cloud Run VPC connector egress settings"
  type        = string
  default     = "PRIVATE_RANGES_ONLY"
}

variable "domain" {
  description = "Optional custom domain for Cloud Run"
  type        = string
  default     = ""
}
