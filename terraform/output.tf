# outputs are values that tf displays after running apply
# its the "return values" from infra deployment

# returns name of s3 bucket
output "bucket_name" {
  description = "S3 bucket for documents and index artifacts"
  value       = aws_s3_bucket.docs.bucket
}

# returns the openai secret ARN
# lmabda fn need arn to read the secret
output "openai_secret_arn" {
  description = "Secrets Manager ARN for the OpenAI API key"
  value       = aws_secretsmanager_secret.openai_api.arn
}

# return base url of API gateway
output "api_base_url" {
  description = "HTTP API base URL"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}