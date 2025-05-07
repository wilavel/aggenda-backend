terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "dynamodb" {
  source     = "./modules/dynamodb"
  table_name = "usuarios"
}

module "lambda" {
  source              = "./modules/lambda"
  function_name       = "crud-usuarios"
  source_code_path    = "${path.module}/lambda"
  dynamodb_table_arn  = module.dynamodb.table_arn
}

module "api_gateway" {
  source            = "./modules/api_gateway"
  api_name          = "crud-api"
  lambda_invoke_arn = module.lambda.invoke_arn
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${module.api_gateway.execution_arn}/*/*/*"
}