provider "aws" {
  region  = var.aws_region
  profile = "agendawa"
}

module "cognito" {
  source = "../../modules/cognito"

  environment           = var.environment
  project_name          = var.project_name
  callback_urls         = var.cognito_callback_urls
  logout_urls           = var.cognito_logout_urls
  existing_user_pool_id = var.cognito_existing_user_pool_id
  existing_client_id    = var.cognito_existing_client_id
}

module "dynamodb" {
  source = "../../modules/dynamodb"

  environment   = var.environment
  project_name  = var.project_name
  billing_mode  = var.dynamodb_billing_mode
  cognito_user_pool_arn = module.cognito.user_pool_arn
}

module "lambda" {
  source = "../../modules/lambda"

  environment           = var.environment
  project_name          = var.project_name
  users_table_name      = module.dynamodb.table_name
  clinics_table_name    = module.dynamodb.clinics_table_name
  users_table_arn       = module.dynamodb.table_arn
  clinics_table_arn     = module.dynamodb.clinics_table_arn
  user_clinic_adscription_table_name = module.dynamodb.user_clinic_adscription_table_name
  cognito_user_pool_id  = module.cognito.user_pool_id
  cognito_user_pool_arn = module.cognito.user_pool_arn
  lambda_zip_path       = var.lambda_zip_path
  lambda_runtime        = var.lambda_runtime
  lambda_timeout        = var.lambda_timeout
  lambda_memory_size    = var.lambda_memory_size
  users_lambda_zip_path        = "../../../dist/users_lambda.zip"
  clinics_lambda_zip_path      = "../../../dist/clinics_lambda.zip"
  whatsapp_lambda_zip_path     = "../../../dist/get_ws_message_lambda.zip"
  email_lambda_zip_path        = "../../../dist/email_lambda.zip"
  availability_lambda_zip_path = "../../../dist/availability_lambda.zip"
  ses_from_email               = "wilavel@gmail.com"
  ses_to_email                 = "centraldent1@gmail.com"
  availability_table_name      = module.dynamodb.doctor_availability_table_name
  availability_table_arn       = module.dynamodb.doctor_availability_table_arn

  whatsapp_verify_token    = var.whatsapp_verify_token
  whatsapp_api_token       = var.whatsapp_api_token
  whatsapp_phone_number_id = var.whatsapp_phone_number_id
}


module "api_gateway" {
  source = "../../modules/api_gateway"

  environment          = var.environment
  project_name         = var.project_name
  lambda_function_name = module.lambda.lambda_function_name
  lambda_invoke_arn    = module.lambda.lambda_invoke_arn
  cognito_user_pool_id         = module.cognito.user_pool_id
  cognito_user_pool_client_id  = module.cognito.client_id
  clinics_lambda_invoke_arn     = module.lambda.clinics_lambda_invoke_arn
  clinics_lambda_function_name  = module.lambda.clinics_lambda_function_name
  whatsapp_lambda_invoke_arn    = module.lambda.whatsapp_lambda_invoke_arn
  whatsapp_lambda_function_name = module.lambda.whatsapp_lambda_function_name
  email_lambda_invoke_arn            = module.lambda.email_lambda_invoke_arn
  email_lambda_function_name         = module.lambda.email_lambda_function_name
  availability_lambda_invoke_arn     = module.lambda.availability_lambda_invoke_arn
  availability_lambda_function_name  = module.lambda.availability_lambda_function_name
}