variable "project_name" {
  description = "Project name for naming resources"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "openai_api_key" {
  description = "OpenAI API key to store in secrets manager"
  type        = string
  sensitive   = true
}