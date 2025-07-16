resource "aws_cloudwatch_log_group" "users_crud" {
  name              = "/aws/lambda/users-crud-${var.environment}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "clinics_crud" {
  name              = "/aws/lambda/clinics-crud-${var.environment}"
  retention_in_days = 14
}
