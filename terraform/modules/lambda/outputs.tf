output "ses_from_email" {
  description = "SES FROM email used in Lambda"
  value       = var.ses_from_email
}

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

output "clinics_lambda_invoke_arn" {
  description = "Invoke ARN of the clinics_crud Lambda function"
  value       = aws_lambda_function.clinics_crud.invoke_arn
}

output "lambda_kms_policy_arn" {
  description = "ARN de la política de KMS para Lambda"
  value       = aws_iam_policy.lambda_kms_policy.arn
}

output "whatsapp_lambda_invoke_arn" {
  description = "Invoke ARN of the WhatsApp webhook Lambda function"
  value       = aws_lambda_function.whatsapp_webhook.invoke_arn
}

output "whatsapp_lambda_function_name" {
  description = "Name of the WhatsApp webhook Lambda function"
  value       = aws_lambda_function.whatsapp_webhook.function_name
}

output "clinics_lambda_function_name" {
  description = "Name of the clinics_crud Lambda function"
  value       = aws_lambda_function.clinics_crud.function_name
}