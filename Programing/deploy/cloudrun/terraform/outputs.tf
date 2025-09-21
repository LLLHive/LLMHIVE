output "cloud_run_url" {
  value       = google_cloud_run_service.llmhive.status[0].url
  description = "Deployed Cloud Run service URL"
}

output "domain_mapping" {
  value       = google_cloud_run_domain_mapping.custom_domain.domain
  description = "Custom domain mapped to the service"
}
