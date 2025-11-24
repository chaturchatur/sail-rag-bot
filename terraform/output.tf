# outputs are values that tf displays after running apply
# its the "return values" from infra deployment

# returns name of s3 bucket
# useful for configuring frontend or scripts
output "bucket_name" {
  description = "S3 bucket for documents and index artifacts"
  value       = aws_s3_bucket.docs.bucket
}

# returns the openai secret arn
# lambda functions need this arn to read the secret at runtime
output "openai_secret_arn" {
  description = "Secrets Manager ARN for the OpenAI API key"
  value       = aws_secretsmanager_secret.openai_api.arn
}

# return base url of api gateway
# this is the url your frontend will call
output "api_base_url" {
  description = "HTTP API base URL"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}