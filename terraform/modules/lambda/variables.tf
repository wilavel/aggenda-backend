variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "users_table_name" {
  description = "Name of the DynamoDB table for users"
  type        = string
}

variable "clinics_table_name" {
  description = "Name of the DynamoDB table for clinics"
  type        = string
}

variable "users_table_arn" {
  description = "ARN of the DynamoDB table for users"
  type        = string
}

variable "clinics_table_arn" {
  description = "ARN of the DynamoDB table for clinics"
  type        = string
}

variable "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  type        = string
}

variable "cognito_user_pool_arn" {
  description = "ARN of the Cognito User Pool"
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to the Lambda function ZIP file"
  type        = string
}

variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.9"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 128
}

variable "ses_from_email" {
  description = "Correo verificado en SES que se usará como remitente en la Lambda."
  type        = string
}

variable "users_lambda_zip_path" {
  description = "Path to the users Lambda function ZIP file"
  type        = string
}

variable "clinics_lambda_zip_path" {
  description = "Path to the clinics Lambda function ZIP file"
  type        = string
} 