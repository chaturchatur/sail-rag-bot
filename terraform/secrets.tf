# creating the container to store the secret in
resource "aws_secretsmanager_secret" "openai_api" {
  name        = "openai/api_key"                 # name of key in aws
  description = "openAI API key for RAG lambdas" # description for documentation purposes lol
}

# the secret value inside the container
resource "aws_secretsmanager_secret_version" "openai_api_v" {
  secret_id     = aws_secretsmanager_secret.openai_api.id # which secret container to put value in
  secret_string = var.openai_api_key                      # actual value of secret itself
}