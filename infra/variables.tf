variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west1"
}

variable "github_repo" {
  description = "GitHub repository (e.g. owner/reddit-scraper)"
  type        = string
}

variable "google_api_key" {
  description = "Gemini API key"
  type        = string
  sensitive   = true
}

variable "gmail_address" {
  description = "Gmail address for sending notifications"
  type        = string
  sensitive   = true
}

variable "gmail_app_password" {
  description = "Gmail app password"
  type        = string
  sensitive   = true
}
