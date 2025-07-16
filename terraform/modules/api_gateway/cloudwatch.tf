resource "aws_cloudwatch_log_group" "users_api" {
  name = "/aws/apigateway/${var.environment}-users-api"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "clinics_api" {
  name = "/aws/apigateway/${var.environment}-clinics-api"
  retention_in_days = 14
}
