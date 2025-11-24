# trust policy - who can use this role
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]    # security token service action for assuming role
    principals {                    # who is allowed to perform the action
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# the role itself
resource "aws_iam_role" "lambda_exec" {
  name               = "${local.project_name}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json # attaches the trust policy
}

# permissions - what this role can do
data "aws_iam_policy_document" "lambda_inline" {
  # rag needs to read/write/list files
  statement {
    effect  = "Allow"                                             # grants access
    actions = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]   # access to download/read, upload/write, list files
    resources = [
      aws_s3_bucket.docs.arn,       # the resource itself - the s3 bucket
      "${aws_s3_bucket.docs.arn}/*" # everything inside the bucket
    ]
  }

  # secret manager to read openai keys
  statement {
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]             # access to read secret value
    resources = [aws_secretsmanager_secret.openai_api.arn]    # references openai key
  }

  # cloudwatch logs for debugging
  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]              # create/write to logs
    resources = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*"]   # all log groups in account
  }

  # dynamodb chat history access
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:BatchWriteItem",    # write multiple items
      "dynamodb:DeleteItem",        # delete items
      "dynamodb:GetItem",           # read single item
      "dynamodb:PutItem",           # write single item
      "dynamodb:Query",             # search items
      "dynamodb:Scan",              # list all items (expensive)
      "dynamodb:UpdateItem",        # update existing item
    ]
    resources = [
      aws_dynamodb_table.messages.arn,
      "${aws_dynamodb_table.messages.arn}/index/*",   # allow access to indexes too
    ]
  }
}

# applies permission to role
resource "aws_iam_role_policy" "lambda_policy" {
  name   = "${local.project_name}-lambda-policy"
  role   = aws_iam_role.lambda_exec.id                        # attach to our lambda role
  policy = data.aws_iam_policy_document.lambda_inline.json    # the policy document defined above
}