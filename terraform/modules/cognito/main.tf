data "aws_cognito_user_pool" "users_pool" {
  user_pool_id = var.existing_user_pool_id
}

data "aws_cognito_user_pool_client" "users_client" {
  user_pool_id = var.existing_user_pool_id
  client_id    = var.existing_client_id
}
