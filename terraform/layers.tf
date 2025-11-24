# layers = shared library folder that multiple lambda functions can use
# without layer lambda downloads entire package on cold start
# with layer its cached faster cold starts 
# FAISS index loading will be faster

locals {
  # paths for zipped layer files
  code_layer_zip       = "${path.module}/build/code_layer.zip"
  faiss_layer_zip      = "${path.module}/build/faiss_layer.zip"
  other_deps_layer_zip = "${path.module}/build/other_deps_layer.zip"
}

# zip shared code (backend.shared)
data "archive_file" "code_layer_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../layers/code"
  output_path = local.code_layer_zip
}

# zip faiss dependencies
data "archive_file" "faiss_layer_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../layers/python"
  output_path = local.faiss_layer_zip
}

# zip other dependencies (openai, pypdf, etc)
data "archive_file" "other_deps_layer_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../layers/deps/"
  output_path = local.other_deps_layer_zip
}

# create shared code layer
# enables sharing common logic across lambdas
resource "aws_lambda_layer_version" "code_layer" {
  layer_name          = "${local.project_name}-shared-code"
  filename            = data.archive_file.code_layer_zip.output_path
  compatible_runtimes = ["python3.11"]
  description         = "Shared application code (backend.shared)"
}

# create faiss layer
# separated due to size and specific dependency needs
resource "aws_lambda_layer_version" "faiss_deps_layer" {
  layer_name          = "${local.project_name}-faiss-deps"
  filename            = data.archive_file.faiss_layer_zip.output_path
  compatible_runtimes = ["python3.11"]
  description         = "FAISS and core numerical dependencies"
}

# create general dependencies layer
# keeps main function packages small
resource "aws_lambda_layer_version" "other_deps_layer" {
  layer_name          = "${local.project_name}-other-deps"
  filename            = data.archive_file.other_deps_layer_zip.output_path
  compatible_runtimes = ["python3.11"]
  description         = "OpenAI, pypdf, httpx, etc."
}