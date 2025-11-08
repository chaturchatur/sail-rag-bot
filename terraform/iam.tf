# trust policy - who can use this role
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"] # security token service of taking/switcing role
    principals {                 # who is allowed to perform the action
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# the role itself
resource "aws_iam_role" "lambda_exec" {
  name               = "${local.project_name}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json # who can use this role
}

# permissions - what this role can do
data "aws_iam_policy_document" "lambda_inline" {
  # RAG needs to read/write/list files
  statement {
    effect  = "Allow"                                           # grants access
    actions = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"] # access to download/read, upload/write, list files to/in s3
    resources = [
      aws_s3_bucket.docs.arn,       # the resource itself - the s3 bucket
      "${aws_s3_bucket.docs.arn}/*" # everything in the bucket
    ]
  }

  # secret manager to read openAI keys
  statement {
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]          # access to read secret value
    resources = [aws_secretsmanager_secret.openai_api.arn] # references openAI key
  }

  # cloudwatch logs
  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]            # create a log group, log stream and write log events
    resources = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*"] # all log groups in the account/region
  }
}

# applies permission to role
resource "aws_iam_role_policy" "lambda_policy" {
  name   = "${local.project_name}-lambda-policy"
  role   = aws_iam_role.lambda_exec.id                     # which role will have the policy
  policy = data.aws_iam_policy_document.lambda_inline.json # the policy itself
}