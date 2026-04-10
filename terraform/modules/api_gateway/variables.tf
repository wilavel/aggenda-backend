variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "lambda_invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  type        = string
}


variable "clinics_lambda_invoke_arn" {
  description = "ARN de invocación de la lambda clinics_crud"
  type        = string
}

variable "clinics_lambda_function_name" {
  description = "Name of the Lambda function for clinics"
  type        = string
}

variable "cognito_user_pool_id" {
  description = "ID del Cognito User Pool para el JWT Authorizer"
  type        = string
}

variable "cognito_user_pool_client_id" {
  description = "ID del Cognito User Pool Client para el JWT Authorizer"
  type        = string
}

variable "whatsapp_lambda_invoke_arn" {
  description = "Invoke ARN of the WhatsApp webhook Lambda function"
  type        = string
}

variable "whatsapp_lambda_function_name" {
  description = "Name of the WhatsApp webhook Lambda function"
  type        = string
}

variable "email_lambda_invoke_arn" {
  description = "Invoke ARN of the email_sender Lambda function"
  type        = string
}

variable "email_lambda_function_name" {
  description = "Name of the email_sender Lambda function"
  type        = string
}

variable "availability_lambda_invoke_arn" {
  description = "Invoke ARN of the availability_crud Lambda function"
  type        = string
}

variable "availability_lambda_function_name" {
  description = "Name of the availability_crud Lambda function"
  type        = string
}

variable "appointments_lambda_invoke_arn" {
  description = "Invoke ARN of the appointments_crud Lambda function"
  type        = string
}

variable "appointments_lambda_function_name" {
  description = "Name of the appointments_crud Lambda function"
  type        = string
}