# name of the project
# used as prefix for resource naming (s3, lambda, dynamo)
variable "project_name" {
  description = "Project name for naming resources"
  type        = string
}

# aws region for deployment
# defaults to us-east-1 (n virginia)
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# openai api key
# used for creating embeddings and chat completions
# sensitive=true prevents it from showing in logs/console
variable "openai_api_key" {
  description = "OpenAI API key to store in secrets manager"
  type        = string
  sensitive   = true
}