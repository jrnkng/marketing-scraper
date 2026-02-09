output "github_variables" {
  description = "Add these as GitHub repository variables (Settings > Secrets and variables > Actions > Variables)"
  value = {
    GCP_PROJECT_ID      = var.project_id
    WIF_PROVIDER        = google_iam_workload_identity_pool_provider.github.name
    WIF_SERVICE_ACCOUNT = google_service_account.deployer.email
  }
}

output "manual_test_command" {
  description = "Run this to test the job manually"
  value       = "gcloud run jobs execute ${local.job_name} --region=${var.region}"
}
