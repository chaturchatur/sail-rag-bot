# lambda is faas, function that runs in the cloud when called 
# serverless, no need to manage server, just pay for execution time
# lambda expects code as a zip file

# zip archive for get_upload_url lambda
data "archive_file" "upload_url_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../backend/lambdas/get_upload_url"
  output_path = "${path.module}/build/get_upload_url.zip"
}

# zip archive for create_session lambda
data "archive_file" "create_session_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../backend/lambdas/create_session"
  output_path = "${path.module}/build/create_session.zip"
}

# zip archive for ingest lambda
data "archive_file" "ingest_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../backend/lambdas/ingest"
  output_path = "${path.module}/build/ingest.zip"
}

# zip archive for query lambda
data "archive_file" "query_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../backend/lambdas/query"
  output_path = "${path.module}/build/query.zip"
}

# zip archive for get_messages lambda
data "archive_file" "get_messages_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../backend/lambdas/get_messages"
  output_path = "${path.module}/build/get_messages.zip"
}

# lambda function: generates presigned urls for uploading files
resource "aws_lambda_function" "get_upload_url" {
  function_name = "${local.project_name}-get-upload-url"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.upload_url_zip.output_path
  timeout       = 10   # short timeout, simple operation
  memory_size   = 256  # minimal memory needed
  architectures = ["x86_64"]

  # attach shared layers
  layers = [
    aws_lambda_layer_version.faiss_deps_layer.arn,
    aws_lambda_layer_version.other_deps_layer.arn,
    aws_lambda_layer_version.code_layer.arn,
  ]

  # environment variables for function logic
  environment {
    variables = {
      BUCKET            = aws_s3_bucket.docs.bucket
      NAMESPACE         = local.namespace
      OPENAI_SECRET_ARN = aws_secretsmanager_secret.openai_api.arn
      EMBED_MODEL       = local.embed_model
      CHAT_MODEL        = local.chat_model
      MESSAGES_TABLE    = aws_dynamodb_table.messages.name
    }
  }
}

# lambda function: creates new chat sessions
resource "aws_lambda_function" "create_session" {
  function_name = "${local.project_name}-create-session"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.create_session_zip.output_path
  timeout       = 10
  memory_size   = 256
  architectures = ["x86_64"]

  layers = [
    aws_lambda_layer_version.faiss_deps_layer.arn,
    aws_lambda_layer_version.other_deps_layer.arn,
    aws_lambda_layer_version.code_layer.arn,
  ]

  environment {
    variables = {
      BUCKET            = aws_s3_bucket.docs.bucket
      NAMESPACE         = local.namespace
      OPENAI_SECRET_ARN = aws_secretsmanager_secret.openai_api.arn
      EMBED_MODEL       = local.embed_model
      CHAT_MODEL        = local.chat_model
      MESSAGES_TABLE    = aws_dynamodb_table.messages.name
    }
  }
}

# lambda function: processes uploaded files, chunks them, and creates vector index
# resource intensive, needs high memory and timeout
resource "aws_lambda_function" "ingest" {
  function_name = "${local.project_name}-ingest"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.ingest_zip.output_path
  timeout       = 900                                         # 15 minutes (max for lambda)
  memory_size   = 3008                                        # high memory for faiss indexing
  architectures = ["x86_64"]

  layers = [
    aws_lambda_layer_version.faiss_deps_layer.arn,
    aws_lambda_layer_version.other_deps_layer.arn,
    aws_lambda_layer_version.code_layer.arn,
  ]

  environment {
    variables = {
      BUCKET            = aws_s3_bucket.docs.bucket
      NAMESPACE         = local.namespace
      OPENAI_SECRET_ARN = aws_secretsmanager_secret.openai_api.arn
      EMBED_MODEL       = local.embed_model
      CHAT_MODEL        = local.chat_model
      MESSAGES_TABLE    = aws_dynamodb_table.messages.name
    }
  }
}

# lambda function: searches index and generates answers
# needs moderate memory for loading index
resource "aws_lambda_function" "query" {
  function_name = "${local.project_name}-query"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.query_zip.output_path
  timeout       = 60                                         # longer timeout for openai latency
  memory_size   = 1024                                       # moderate memory for index search
  architectures = ["x86_64"]

  layers = [
    aws_lambda_layer_version.faiss_deps_layer.arn,
    aws_lambda_layer_version.other_deps_layer.arn,
    aws_lambda_layer_version.code_layer.arn,
  ]

  environment {
    variables = {
      BUCKET            = aws_s3_bucket.docs.bucket
      NAMESPACE         = local.namespace
      OPENAI_SECRET_ARN = aws_secretsmanager_secret.openai_api.arn
      EMBED_MODEL       = local.embed_model
      CHAT_MODEL        = local.chat_model
      MESSAGES_TABLE    = aws_dynamodb_table.messages.name
    }
  }
}

# lambda function: retrieves conversation history
resource "aws_lambda_function" "get_messages" {
  function_name = "${local.project_name}-get-messages"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.get_messages_zip.output_path
  timeout       = 10
  memory_size   = 256
  architectures = ["x86_64"]

  layers = [
    aws_lambda_layer_version.faiss_deps_layer.arn,
    aws_lambda_layer_version.other_deps_layer.arn,
    aws_lambda_layer_version.code_layer.arn,
  ]

  environment {
    variables = {
      BUCKET            = aws_s3_bucket.docs.bucket
      NAMESPACE         = local.namespace
      OPENAI_SECRET_ARN = aws_secretsmanager_secret.openai_api.arn
      EMBED_MODEL       = local.embed_model
      CHAT_MODEL        = local.chat_model
      MESSAGES_TABLE    = aws_dynamodb_table.messages.name
    }
  }
}