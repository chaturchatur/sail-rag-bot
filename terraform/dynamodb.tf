# create dynamodb table for storing chat history
resource "aws_dynamodb_table" "messages" {
  name         = "${local.project_name}-messages"
  billing_mode = "PAY_PER_REQUEST"                    # on demand pricing so no need to pay for idle time
  hash_key     = "sessionKey"                         # partition key: combines namespace and session id
  range_key    = "timestamp"                          # sort key: orders messages by time
  
  # partition key attribute
  attribute {
    name = "sessionKey"
    type = "S"            # string type
  }

  # sort key attribute
  attribute {
    name = "timestamp"
    type = "S"           # string type
  }

  # enable automatic backups (pitr)
  # allows restoring table in the last 35 days
  point_in_time_recovery {
    enabled = true
  }

  # project tags for resource management
  tags = {
    Project = local.project_name
  }
}