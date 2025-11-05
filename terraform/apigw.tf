# API gateway for creating HTTP APIs that route requests to backend lambda functions

# creating the main API container
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${local.project_name}-http-api"
  protocol_type = "HTTP" # REST API 

  # cors configuration
  cors_configuration {
    allow_origins = [
      "http://localhost:3000",
      "https://bidayx9gga.execute-api.us-east-1.amazonaws.com" # optional
    ]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
    expose_headers = ["content-type"]
    max_age        = 3600
  }
}

# integrating with backend/lambda function
# connects API gateway to lambda function
# get presigned url for file upload
resource "aws_apigatewayv2_integration" "upload_url" {
  api_id                 = aws_apigatewayv2_api.http_api.id              # which API this integration belongs to
  integration_type       = "AWS_PROXY"                                   # aws_proxy = forward everything to lambda
  integration_uri        = aws_lambda_function.get_upload_url.invoke_arn # address for the lambda function
  integration_method     = "POST"                                        # always POST for lambda
  payload_format_version = "2.0"                                         # new simpler version format 
}

# process uploaded docs, build search index
resource "aws_apigatewayv2_integration" "ingest" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.ingest.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# answer questions using the index
resource "aws_apigatewayv2_integration" "query" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.query.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# route/ url mapping
# maps HTTP requests to integrations
resource "aws_apigatewayv2_route" "route_upload_url" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /upload-url"                                           # when someone POSTs to /upload-url
  target    = "integrations/${aws_apigatewayv2_integration.upload_url.id}" # points to integration or which lambda to call
}

resource "aws_apigatewayv2_route" "route_ingest" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /ingest"
  target    = "integrations/${aws_apigatewayv2_integration.ingest.id}"
}

resource "aws_apigatewayv2_route" "route_query" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /query"
  target    = "integrations/${aws_apigatewayv2_integration.query.id}"
}

# stage/ deployment environment
# creates a deployment stage 
# makes API actually live and accessible to users
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default" # default stage name
  auto_deploy = true       # auto deploys changes when routes are updated
}

# lambda permission/security
# allow API Gateway to invoke lambdas
# lambdas cant be called by other service
# this allows api gateway to call them
resource "aws_lambda_permission" "apigw_upload_url" {
  statement_id  = "AllowAPIGatewayInvokeUploadURL"
  action        = "lambda:InvokeFunction" # permission to call the function
  function_name = aws_lambda_function.get_upload_url.function_name
  principal     = "apigateway.amazonaws.com" # API gateway service
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "apigw_ingest" {
  statement_id  = "AllowAPIGatewayInvokeIngest"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "apigw_query" {
  statement_id  = "AllowAPIGatewayInvokeQuery"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}