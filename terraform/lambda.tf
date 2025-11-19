# lambda is faas, function that runs in the cloud when called 
# serverless, no need to manage server, just pay for execution time
# lambda expects code as a zip file
data "archive_file" "upload_url_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../backend/lambdas/get_upload_url"
  output_path = "${path.module}/build/get_upload_url.zip"
}

data "archive_file" "create_session_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../backend/lambdas/create_session"
  output_path = "${path.module}/build/create_session.zip"
}

data "archive_file" "ingest_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../backend/lambdas/ingest"
  output_path = "${path.module}/build/ingest.zip"
}

data "archive_file" "query_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../backend/lambdas/query"
  output_path = "${path.module}/build/query.zip"
}

# Archive file for get_messages lambda
data "archive_file" "get_messages_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../backend/lambdas/get_messages"
  output_path = "${path.module}/build/get_messages.zip"
}

resource "aws_lambda_function" "get_upload_url" {
  function_name = "${local.project_name}-get-upload-url"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.upload_url_zip.output_path
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

resource "aws_lambda_function" "ingest" {
  function_name = "${local.project_name}-ingest"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.ingest_zip.output_path
  timeout       = 900
  memory_size   = 3008
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

resource "aws_lambda_function" "query" {
  function_name = "${local.project_name}-query"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.query_zip.output_path
  timeout       = 60
  memory_size   = 1024
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

# Lambda function for retrieving conversation history
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