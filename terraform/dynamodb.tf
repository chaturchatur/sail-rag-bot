resource "aws_dynamodb_table" "messages" {
  name         = "${local.project_name}-messages"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sessionKey"
  range_key    = "timestamp"

  attribute {
    name = "sessionKey"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Project = local.project_name
  }
}