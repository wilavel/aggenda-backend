provider "aws" {
  region = var.aws_region
}

module "cognito" {
  source = "../../modules/cognito"

  environment    = var.environment
  project_name   = var.project_name
  callback_urls  = var.cognito_callback_urls
  logout_urls    = var.cognito_logout_urls
}

module "dynamodb" {
  source = "../../modules/dynamodb"

  environment   = var.environment
  project_name  = var.project_name
  billing_mode  = var.dynamodb_billing_mode
}

module "lambda" {
  source = "../../modules/lambda"

  environment           = var.environment
  project_name          = var.project_name
  dynamodb_table_name   = module.dynamodb.table_name
  dynamodb_table_arn    = module.dynamodb.table_arn
  cognito_user_pool_id  = module.cognito.user_pool_id
  cognito_user_pool_arn = module.cognito.user_pool_arn
  lambda_zip_path       = var.lambda_zip_path
  lambda_runtime        = var.lambda_runtime
  lambda_timeout        = var.lambda_timeout
  lambda_memory_size    = var.lambda_memory_size
  users_lambda_zip_path   = "../../../dist/users_lambda.zip"
  clinics_lambda_zip_path = "../../../dist/clinics_lambda.zip"
  ses_from_email         = "wilavel@gmail.com" # Cambia esto por tu correo verificado en SES
}

module "api_gateway" {
  source = "../../modules/api_gateway"

  environment          = var.environment
  project_name         = var.project_name
  lambda_function_name = module.lambda.lambda_function_name
  lambda_invoke_arn    = module.lambda.lambda_invoke_arn
  cognito_user_pool_id         = module.cognito.user_pool_id
  cognito_user_pool_client_id  = module.cognito.client_id
  clinics_lambda_invoke_arn    = module.lambda.clinics_lambda_invoke_arn
}