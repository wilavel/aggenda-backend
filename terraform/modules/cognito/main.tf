resource "aws_cognito_user_pool" "users_pool" {
  name = "${var.environment}-users-pool"

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    mutable            = true
    required           = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  schema {
    name                = "name"
    attribute_data_type = "String"
    mutable            = true
    required           = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  auto_verified_attributes = ["email"]

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cognito_user_pool_client" "users_client" {
  name = "${var.environment}-users-client"

  user_pool_id = aws_cognito_user_pool.users_pool.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_CUSTOM_AUTH"
  ]

  allowed_oauth_flows = ["code", "implicit"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes = ["email", "openid", "profile"]

  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls

  supported_identity_providers = ["COGNITO"]

  prevent_user_existence_errors = "ENABLED"
  
  token_validity_units {
    refresh_token = "days"
    access_token  = "hours"
    id_token      = "hours"
  }

  refresh_token_validity = 30
  access_token_validity  = 1
  id_token_validity     = 1
}

resource "aws_cognito_user_group" "administrator_group" {
  user_pool_id = aws_cognito_user_pool.users_pool.id
  name         = "Administrator"
  description  = "Grupo de administradores"
  precedence   = 1
}

resource "aws_cognito_user_group" "managers" {
  user_pool_id = aws_cognito_user_pool.users_pool.id
  name         = "managers"
  description  = "Grupo de managers"
  precedence   = 2
}

resource "aws_cognito_user_group" "clients" {
  user_pool_id = aws_cognito_user_pool.users_pool.id
  name         = "clients"
  description  = "Grupo de clientes"
  precedence   = 3
}

resource "aws_cognito_user_group" "medicos" {
  user_pool_id = aws_cognito_user_pool.users_pool.id
  name         = "medicos"
  description  = "Grupo de médicos"
  precedence   = 4
} 