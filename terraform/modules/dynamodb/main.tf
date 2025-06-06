resource "aws_dynamodb_table" "users_table" {
  name           = "${var.environment}-users"
  billing_mode   = var.billing_mode
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Name        = "${var.environment}-users-table"
    Environment = var.environment
    Project     = var.project_name
  }
} 