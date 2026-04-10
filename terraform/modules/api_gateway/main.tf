resource "aws_apigatewayv2_api" "users_api" {
  name          = "${var.environment}-users-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["*"]
    allow_methods = ["*"]
    allow_origins = ["*"]
    expose_headers = ["*"]
    max_age = 300
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id = aws_apigatewayv2_api.users_api.id
  authorizer_type = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name = "cognito-jwt-authorizer"
  jwt_configuration {
    audience = [var.cognito_user_pool_client_id]
    issuer   = "https://cognito-idp.us-east-1.amazonaws.com/${var.cognito_user_pool_id}"
  }
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.users_api.id
  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  description            = "Lambda integration"
  integration_method     = "POST"
  integration_uri        = var.lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.users_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "clinics_api_gw" {
  statement_id  = "AllowExecutionFromAPIGatewayClinics"
  action        = "lambda:InvokeFunction"
  function_name = var.clinics_lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.users_api.execution_arn}/*/*"
}


resource "aws_apigatewayv2_route" "get_users" {
  api_id    = aws_apigatewayv2_api.users_api.id
  route_key = "GET /users"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Email Lambda integration and route (no authentication required)
resource "aws_apigatewayv2_integration" "email_integration" {
  api_id                 = aws_apigatewayv2_api.users_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.email_lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_lambda_permission" "email_api_gw" {
  statement_id  = "AllowExecutionFromAPIGatewayEmail"
  action        = "lambda:InvokeFunction"
  function_name = var.email_lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.users_api.execution_arn}/*/*"
}

resource "aws_apigatewayv2_route" "send_json_email" {
  api_id    = aws_apigatewayv2_api.users_api.id
  route_key = "POST /send-json-email"
  target    = "integrations/${aws_apigatewayv2_integration.email_integration.id}"
}


# API Routes protegidas con JWT Authorizer
resource "aws_apigatewayv2_route" "post_users" {
  api_id    = aws_apigatewayv2_api.users_api.id
  route_key = "POST /users"
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

# API Gateway Routes for Clinics
resource "aws_apigatewayv2_route" "post_clinics" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "POST /clinics"
  target             = "integrations/${aws_apigatewayv2_integration.clinics_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "get_clinics" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "GET /clinics"
  target             = "integrations/${aws_apigatewayv2_integration.clinics_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "get_clinic" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "GET /clinics/{clinic_id}"
  target             = "integrations/${aws_apigatewayv2_integration.clinics_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "put_clinic" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "PUT /clinics/{clinic_id}"
  target             = "integrations/${aws_apigatewayv2_integration.clinics_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "delete_clinic" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "DELETE /clinics/{clinic_id}"
  target             = "integrations/${aws_apigatewayv2_integration.clinics_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

# Lambda Integration for Clinics
resource "aws_apigatewayv2_integration" "clinics_integration" {
  api_id           = aws_apigatewayv2_api.users_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = var.clinics_lambda_invoke_arn
  payload_format_version = "2.0"
}


# WhatsApp Webhook Integration (sin autenticación)
resource "aws_apigatewayv2_integration" "whatsapp_integration" {
  api_id                 = aws_apigatewayv2_api.users_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.whatsapp_lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_lambda_permission" "whatsapp_api_gw" {
  statement_id  = "AllowExecutionFromAPIGatewayWhatsApp"
  action        = "lambda:InvokeFunction"
  function_name = var.whatsapp_lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.users_api.execution_arn}/*/*"
}

# ── Doctor Availability ───────────────────────────────────────────────────────
resource "aws_apigatewayv2_integration" "availability_integration" {
  api_id                 = aws_apigatewayv2_api.users_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.availability_lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_lambda_permission" "availability_api_gw" {
  statement_id  = "AllowExecutionFromAPIGatewayAvailability"
  action        = "lambda:InvokeFunction"
  function_name = var.availability_lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.users_api.execution_arn}/*/*"
}

resource "aws_apigatewayv2_route" "post_doctor_availability" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "POST /doctors/{doctor_id}/availability"
  target             = "integrations/${aws_apigatewayv2_integration.availability_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "get_doctor_availability" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "GET /doctors/{doctor_id}/availability"
  target             = "integrations/${aws_apigatewayv2_integration.availability_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "put_doctor_availability" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "PUT /doctors/{doctor_id}/availability/{slot_id}"
  target             = "integrations/${aws_apigatewayv2_integration.availability_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "delete_doctor_availability" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "DELETE /doctors/{doctor_id}/availability/{slot_id}"
  target             = "integrations/${aws_apigatewayv2_integration.availability_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "get_clinic_availability" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "GET /clinics/{clinic_id}/availability"
  target             = "integrations/${aws_apigatewayv2_integration.availability_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

# ── Appointments ──────────────────────────────────────────────────────────────
resource "aws_apigatewayv2_integration" "appointments_integration" {
  api_id                 = aws_apigatewayv2_api.users_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.appointments_lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_lambda_permission" "appointments_api_gw" {
  statement_id  = "AllowExecutionFromAPIGatewayAppointments"
  action        = "lambda:InvokeFunction"
  function_name = var.appointments_lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.users_api.execution_arn}/*/*"
}

resource "aws_apigatewayv2_route" "post_appointments" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "POST /appointments"
  target             = "integrations/${aws_apigatewayv2_integration.appointments_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "get_appointment" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "GET /appointments/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.appointments_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "delete_appointment" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "DELETE /appointments/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.appointments_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "get_doctor_appointments" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "GET /doctors/{doctor_id}/appointments"
  target             = "integrations/${aws_apigatewayv2_integration.appointments_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "get_patient_appointments" {
  api_id             = aws_apigatewayv2_api.users_api.id
  route_key          = "GET /patients/{patient_id}/appointments"
  target             = "integrations/${aws_apigatewayv2_integration.appointments_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

# GET /whatsapp/webhook — verificación del webhook de Meta
resource "aws_apigatewayv2_route" "whatsapp_verify" {
  api_id    = aws_apigatewayv2_api.users_api.id
  route_key = "GET /whatsapp/webhook"
  target    = "integrations/${aws_apigatewayv2_integration.whatsapp_integration.id}"
}

# POST /whatsapp/webhook — recepción de mensajes de Meta
resource "aws_apigatewayv2_route" "whatsapp_messages" {
  api_id    = aws_apigatewayv2_api.users_api.id
  route_key = "POST /whatsapp/webhook"
  target    = "integrations/${aws_apigatewayv2_integration.whatsapp_integration.id}"
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id = aws_apigatewayv2_api.users_api.id
  name   = var.environment
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.users_api.arn
    format = jsonencode({
      requestId       = "$context.requestId"
      ip              = "$context.identity.sourceIp"
      requestTime     = "$context.requestTime"
      httpMethod      = "$context.httpMethod"
      routeKey        = "$context.routeKey"
      status          = "$context.status"
      protocol        = "$context.protocol"
      responseLength  = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      authorizer      = "$context.authorizer.claims"
    })
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_apigatewayv2_stage" "clinics_prod" {
  api_id = aws_apigatewayv2_api.users_api.id
  name   = "clinics-${var.environment}"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.clinics_api.arn
    format = jsonencode({
      requestId       = "$context.requestId"
      ip              = "$context.identity.sourceIp"
      requestTime     = "$context.requestTime"
      httpMethod      = "$context.httpMethod"
      routeKey        = "$context.routeKey"
      status          = "$context.status"
      protocol        = "$context.protocol"
      responseLength  = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      authorizer      = "$context.authorizer.claims"
    })
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}
 