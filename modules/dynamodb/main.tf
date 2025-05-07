resource "aws_dynamodb_table" "this" {
  name         = var.table_name  # ¡Usa la variable aquí!
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}