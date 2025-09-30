output "service_url" {
  description = "Deployed Cloud Run service URL"
  value       = google_cloud_run_service.llmhive.status[0].url
}

output "domain_mapping_status" {
  description = "DNS records required for the optional custom domain"
  value       = var.domain == "" ? null : google_cloud_run_domain_mapping.custom_domain[0].status[0].resource_records
}
