# Example Terraform variables for Cloud Run deployment (copy to env.auto.tfvars and edit)
project_id        = "llmhive-demo-12345"        # GCP Project ID
region            = "us-central1"               # GCP region for Cloud Run and other resources
service_name      = "llmhive-api"               # Name for the Cloud Run service
image_repository  = "<<AR_REPO>>"               # Artifact Registry repository name (where image is stored)
image_tag         = "<<IMAGE_TAG>>"             # Docker image tag to deploy
ingress_hostname  = "LLMMHIVE.AI"               # Custom domain to map to Cloud Run (must be verified in Cloud DNS)
vpc_connector_name= "llmhive-connector"         # Name of the VPC connector (for DB access)
db_user           = "<<DB_USER>>"               # Postgres username (for Cloud SQL instance)
db_pass           = "<<DB_PASS>>"               # Postgres password
db_name           = "<<DB_NAME>>"               # Database name
cloudsql_private_ip = "<<CLOUDSQL_IP>>"         # Private IP of the Cloud SQL instance (for direct connection)
