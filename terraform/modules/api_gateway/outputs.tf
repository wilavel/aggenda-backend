output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "${aws_apigatewayv2_api.users_api.api_endpoint}/${aws_apigatewayv2_stage.prod.name}"
} 