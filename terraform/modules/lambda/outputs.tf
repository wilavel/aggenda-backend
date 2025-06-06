output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.users_crud.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.users_crud.arn
}

output "lambda_invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  value       = aws_lambda_function.users_crud.invoke_arn
} 