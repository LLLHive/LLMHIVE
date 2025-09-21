output "service_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.llmhive.status[0].url
}

output "domain_status" {
  description = "Status of the custom domain mapping"
  value       = try(google_cloud_run_domain_mapping.custom_domain.status[0].resource_records, [])
}
