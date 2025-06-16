terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "environment" {
  description = "Environment (dev or prod)"
  type        = string
  default     = "dev"
}

locals {
  environment = var.environment
  tags = {
    Environment = local.environment
    Name        = "users-api-${local.environment}"
  }
}

# DynamoDB Table
resource "aws_dynamodb_table" "users_table" {
  name           = "users-${local.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = local.tags
}

# Doctors Table
resource "aws_dynamodb_table" "doctors_table" {
  name           = "doctors-${local.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "specialty"
    type = "S"
  }

  global_secondary_index {
    name            = "SpecialtyIndex"
    hash_key        = "specialty"
    projection_type = "ALL"
  }

  tags = local.tags
}

# Patients Table
resource "aws_dynamodb_table" "patients_table" {
  name           = "patients-${local.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = local.tags
}

# Clinics Table
resource "aws_dynamodb_table" "clinics_table" {
  name           = "clinics-${local.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = local.tags
}

# Appointments Table
resource "aws_dynamodb_table" "appointments_table" {
  name           = "appointments-${local.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "doctor_id"
    type = "S"
  }

  attribute {
    name = "patient_id"
    type = "S"
  }

  attribute {
    name = "appointment_date"
    type = "S"
  }

  global_secondary_index {
    name            = "DoctorAppointmentsIndex"
    hash_key        = "doctor_id"
    range_key       = "appointment_date"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "PatientAppointmentsIndex"
    hash_key        = "patient_id"
    range_key       = "appointment_date"
    projection_type = "ALL"
  }

  tags = local.tags
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "lambda_dynamodb_role_${local.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for DynamoDB access
resource "aws_iam_policy" "lambda_dynamodb_policy" {
  name        = "lambda_dynamodb_policy_${local.environment}"
  description = "IAM policy for Lambda to access DynamoDB and Cognito"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Effect   = "Allow"
        Resource = [
          aws_dynamodb_table.users_table.arn,
          aws_dynamodb_table.doctors_table.arn,
          aws_dynamodb_table.patients_table.arn,
          aws_dynamodb_table.clinics_table.arn,
          aws_dynamodb_table.appointments_table.arn,
          "${aws_dynamodb_table.doctors_table.arn}/index/*",
          "${aws_dynamodb_table.appointments_table.arn}/index/*"
        ]
      },
      {
        Action = [
          "cognito-idp:AdminListGroupsForUser",
          "cognito-idp:AdminGetUser",
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminSetUserPassword",
          "cognito-idp:AdminInitiateAuth",
          "cognito-idp:AdminRespondToAuthChallenge",
          "cognito-idp:AdminAddUserToGroup",
          "cognito-idp:AdminListGroups",
          "cognito-idp:AdminGetGroup",
          "cognito-idp:AdminDeleteUser",
          "cognito-idp:AdminRemoveUserFromGroup",
          "cognito-idp:GetGroup",
          "cognito-idp:CreateGroup"
        ]
        Effect   = "Allow"
        Resource = aws_cognito_user_pool.users.arn
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "lambda_dynamodb_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_dynamodb_policy.arn
}

# Lambda Permission
resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.users_crud.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.users_api.execution_arn}/*/*"
}

# Lambda Logs Policy
resource "aws_iam_role_policy_attachment" "lambda_logs_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda Function
resource "aws_lambda_function" "users_crud" {
  filename         = "lambda_function.zip"
  function_name    = "users-crud-${local.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "users_function.lambda_handler"
  runtime         = "python3.9"
  timeout         = 30
  memory_size     = 128

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.users_table.name
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.users.id
    }
  }
}

# API Gateway
resource "aws_apigatewayv2_api" "users_api" {
  name          = "users-api-${local.environment}"
  protocol_type = "HTTP"
  cors_configuration {
    allow_headers = ["*"]
    allow_methods = ["*"]
    allow_origins = ["*"]
    expose_headers = ["*"]
    max_age = 300
  }
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "dev" {
  api_id = aws_apigatewayv2_api.users_api.id
  name   = local.environment
  auto_deploy = true
}

# Lambda Integration
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.users_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.users_crud.invoke_arn
  integration_method = "POST"
  payload_format_version = "1.0"
}

# Cognito User Pool
resource "aws_cognito_user_pool" "users" {
  name = "users-pool-${local.environment}"

  # Configuración para usar email como método de inicio de sesión
  username_attributes = ["email"]
  auto_verified_attributes = ["email"]

  # Configuración de políticas de contraseña
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  # Configuración de verificación de email
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject = "Tu código de verificación"
    email_message = "Tu código de verificación es {####}"
  }

  # Configuración de esquema de atributos
  schema {
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    name                     = "email"
    required                 = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # Configuración de políticas de usuario
  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  # Configuración de MFA
  mfa_configuration = "OFF"

  # Configuración de recuperación de cuenta
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "users_client" {
  name         = "users-client-${local.environment}"
  user_pool_id = aws_cognito_user_pool.users.id
  generate_secret = false

  # Configuración de flujos de autenticación
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_ADMIN_USER_PASSWORD_AUTH"
  ]

  # Configuración de OAuth
  allowed_oauth_flows = ["code", "implicit"]
  allowed_oauth_scopes = ["email", "openid", "profile"]
  allowed_oauth_flows_user_pool_client = true

  # URLs de callback y logout
  callback_urls = ["https://example.com/callback"]
  logout_urls   = ["https://example.com/logout"]

  # Proveedores de identidad soportados
  supported_identity_providers = ["COGNITO"]

  # Configuración de tokens
  refresh_token_validity = 30
  access_token_validity  = 1
  id_token_validity     = 1
}

# Cognito Groups
resource "aws_cognito_user_group" "doctors" {
  name         = "doctors"
  user_pool_id = aws_cognito_user_pool.users.id
  description  = "Group for medical doctors"
  precedence   = 1
}

resource "aws_cognito_user_group" "patients" {
  name         = "patients"
  user_pool_id = aws_cognito_user_pool.users.id
  description  = "Group for patients"
  precedence   = 2
}

resource "aws_cognito_user_group" "managers" {
  name         = "managers"
  user_pool_id = aws_cognito_user_pool.users.id
  description  = "Group for clinic managers"
  precedence   = 3
}

# API Gateway JWT Authorizer
resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id = aws_apigatewayv2_api.users_api.id
  authorizer_type = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name = "cognito-jwt-authorizer"
  jwt_configuration {
    audience = [aws_cognito_user_pool_client.users_client.id]
    issuer   = "https://cognito-idp.us-east-1.amazonaws.com/${aws_cognito_user_pool.users.id}"
  }
}

# API Routes protegidas con JWT Authorizer
resource "aws_apigatewayv2_route" "post_users" {
  api_id    = aws_apigatewayv2_api.users_api.id
  route_key = "POST /users"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
  authorizer_id = aws_apigatewayv2_authorizer.jwt.id
  authorization_type = "JWT"
}

resource "aws_apigatewayv2_route" "get_users" {
  api_id    = aws_apigatewayv2_api.users_api.id
  route_key = "GET /users"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
  authorizer_id = aws_apigatewayv2_authorizer.jwt.id
  authorization_type = "JWT"
}

resource "aws_apigatewayv2_route" "get_user" {
  api_id    = aws_apigatewayv2_api.users_api.id
  route_key = "GET /users/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
  authorizer_id = aws_apigatewayv2_authorizer.jwt.id
  authorization_type = "JWT"
}

resource "aws_apigatewayv2_route" "put_user" {
  api_id    = aws_apigatewayv2_api.users_api.id
  route_key = "PUT /users/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
  authorizer_id = aws_apigatewayv2_authorizer.jwt.id
  authorization_type = "JWT"
}

resource "aws_apigatewayv2_route" "delete_user" {
  api_id    = aws_apigatewayv2_api.users_api.id
  route_key = "DELETE /users/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
  authorizer_id = aws_apigatewayv2_authorizer.jwt.id
  authorization_type = "JWT"
}

# Ruta para login (sin autorización)
resource "aws_apigatewayv2_route" "login" {
  api_id    = aws_apigatewayv2_api.users_api.id
  route_key = "POST /login"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

output "api_endpoint" {
  value = "${aws_apigatewayv2_api.users_api.api_endpoint}/${local.environment}"
  description = "The URL of the API Gateway endpoint"
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.users.id
  description = "Cognito User Pool ID"
}

output "cognito_user_pool_client_id" {
  value = aws_cognito_user_pool_client.users_client.id
  description = "Cognito User Pool Client ID"
} 