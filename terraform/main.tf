# tf config block
# defines required providers and backend settings
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

# configure aws provider
# specify region where resources are created
provider "aws" {
  region = var.region
}

# global context
locals {
  project_name = var.project_name
  bucket_name  = "rag-docs-${var.project_name}"
  namespace    = "default"
  embed_model  = "text-embedding-3-small"
  chat_model   = "gpt-4o-mini"
}

# gets identity of current aws account
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}