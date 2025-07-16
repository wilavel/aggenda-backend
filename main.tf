module "cognito" {
  source       = "./terraform/modules/cognito"
  environment  = var.environment
}

module "dynamodb" {
  source                  = "./terraform/modules/dynamodb"
  environment             = var.environment
  project_name            = var.project_name
  billing_mode            = var.billing_mode # Opcional, tiene valor por default
  cognito_user_pool_arn   = module.cognito.user_pool_arn
}

