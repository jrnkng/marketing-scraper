terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_project" "this" {}

locals {
  job_name = "reddit-scraper"
  # Placeholder image for initial deploy; CI/CD will replace it
  initial_image = "us-docker.pkg.dev/cloudrun/container/hello"
}

# ── APIs ───────────────────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "secretmanager.googleapis.com",
    "iamcredentials.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# ── Artifact Registry ──────────────────────────────────────────────

resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = local.job_name
  format        = "DOCKER"

  depends_on = [google_project_service.apis]
}

# ── Secrets ────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "google_api_key" {
  secret_id = "google-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "google_api_key" {
  secret      = google_secret_manager_secret.google_api_key.id
  secret_data = var.google_api_key
}

resource "google_secret_manager_secret" "gmail_address" {
  secret_id = "gmail-address"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "gmail_address" {
  secret      = google_secret_manager_secret.gmail_address.id
  secret_data = var.gmail_address
}

resource "google_secret_manager_secret" "gmail_app_password" {
  secret_id = "gmail-app-password"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "gmail_app_password" {
  secret      = google_secret_manager_secret.gmail_app_password.id
  secret_data = var.gmail_app_password
}

# ── Cloud Run Job ──────────────────────────────────────────────────

resource "google_cloud_run_v2_job" "scraper" {
  name                = local.job_name
  location            = var.region
  deletion_protection = false

  template {
    task_count = 1

    template {
      timeout     = "600s"
      max_retries = 1

      containers {
        image = local.initial_image

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name = "GOOGLE_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.google_api_key.secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "GMAIL_ADDRESS"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.gmail_address.secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "GMAIL_APP_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.gmail_app_password.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  depends_on = [google_project_service.apis]

  lifecycle {
    ignore_changes = [
      # CI/CD updates the image on every deploy
      template[0].template[0].containers[0].image,
    ]
  }
}

# Grant the Cloud Run service agent access to secrets
resource "google_secret_manager_secret_iam_member" "run_access" {
  for_each = {
    google_api_key   = google_secret_manager_secret.google_api_key.id
    gmail_address    = google_secret_manager_secret.gmail_address.id
    gmail_app_password = google_secret_manager_secret.gmail_app_password.id
  }

  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.this.number}-compute@developer.gserviceaccount.com"
}

# ── Cloud Scheduler ────────────────────────────────────────────────

resource "google_cloud_scheduler_job" "trigger" {
  name     = "${local.job_name}-trigger"
  region   = var.region
  schedule = "0 */2 * * *"

  http_target {
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${local.job_name}:run"
    http_method = "POST"

    oauth_token {
      service_account_email = "${data.google_project.this.number}-compute@developer.gserviceaccount.com"
    }
  }

  depends_on = [google_cloud_run_v2_job.scraper]
}

# ── Workload Identity Federation (GitHub Actions) ──────────────────

resource "google_service_account" "deployer" {
  account_id   = "${local.job_name}-deployer"
  display_name = "Reddit Scraper Deployer"
}

resource "google_project_iam_member" "deployer_roles" {
  for_each = toset([
    "roles/run.developer",
    "roles/artifactregistry.writer",
    "roles/iam.serviceAccountUser",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions-provider"
  display_name                       = "GitHub Actions"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "assertion.repository == '${var.github_repo}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}
