# API gateway for creating HTTP APIs that route requests to backend lambda functions

# creating the main API container
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${local.project_name}-http-api"
  protocol_type = "HTTP" # REST API 

  # cors configuration
  cors_configuration {
    allow_origins = [
      "http://localhost:3000"
    ]
    allow_methods  = ["GET", "POST", "OPTIONS"]
    allow_headers  = ["content-type", "authorization"]
    expose_headers = ["content-type"]
    max_age        = 3600
  }
}

resource "aws_cloudwatch_log_group" "http_api_access" {
  name              = "/aws/apigateway/${local.project_name}-http-access"
  retention_in_days = 14
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

resource "aws_apigatewayv2_integration" "create_session" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.create_session.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
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

# retrieve conversation history for a session
resource "aws_apigatewayv2_integration" "get_messages" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_messages.invoke_arn
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

resource "aws_apigatewayv2_route" "route_create_session" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /sessions"
  target    = "integrations/${aws_apigatewayv2_integration.create_session.id}"
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

resource "aws_apigatewayv2_route" "route_get_messages" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /sessions/{sessionId}/messages"
  target    = "integrations/${aws_apigatewayv2_integration.get_messages.id}"
}

# stage/ deployment environment
# creates a deployment stage 
# makes API actually live and accessible to users
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default" # default stage name
  auto_deploy = true       # auto deploys changes when routes are updated

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.http_api_access.arn
    format = jsonencode({
      requestId         : "$context.requestId",
      requestTime       : "$context.requestTime",
      httpMethod        : "$context.httpMethod",
      routeKey          : "$context.routeKey",
      status            : "$context.status",
      integrationStatus : "$context.integrationStatus",
      errorMessage      : "$context.error.message",
      responseLatency   : "$context.responseLatency",
      ip                : "$context.identity.sourceIp",
      userAgent         : "$context.identity.userAgent",
      protocol          : "$context.protocol"
    })
  }
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

resource "aws_lambda_permission" "apigw_create_session" {
  statement_id  = "AllowAPIGatewayInvokeCreateSession"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_session.function_name
  principal     = "apigateway.amazonaws.com"
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

resource "aws_lambda_permission" "apigw_get_messages" {
  statement_id  = "AllowAPIGatewayInvokeGetMessages"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_messages.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}