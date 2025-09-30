project = "your-gcp-project"
region  = "us-central1"
image   = "us-central1-docker.pkg.dev/your-gcp-project/llmhive/llmhive:latest"
service_account_email = "llmhive-run@your-gcp-project.iam.gserviceaccount.com"
database_secret = "projects/your-gcp-project/secrets/llmhive_database_url"
# database_secret_version = "latest"
# environment = { OPENAI_API_BASE = "https://api.openai.com/v1" }
# secret_environment_variables = [
#   { name = "OPENAI_API_KEY", secret = "projects/your-gcp-project/secrets/openai_api_key", version = "latest" }
# ]
# vpc_create_connector = true
# vpc_network = "default"
# vpc_connector_cidr = "10.8.0.0/28"
# domain = "llmhive.ai"
