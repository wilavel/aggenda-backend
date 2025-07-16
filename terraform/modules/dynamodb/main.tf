# DynamoDB Tables
resource "aws_dynamodb_table" "users_table" {
  name           = "users-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Name        = "services-api-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "clinics_table" {
  name           = "clinics-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"
}

resource "aws_dynamodb_table" "user_clinic_adscription" {
  name         = "user-clinic-adscription-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "clinic_id"

  attribute {
    name = "user_id"
    type = "S"
  }
  attribute {
    name = "clinic_id"
    type = "S"
  }

  tags = {
    Name        = "user-clinic-adscription-${var.environment}"
    Environment = var.environment
  }
}

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Name        = "services-api-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "doctors_table" {
  name           = "doctors-${var.environment}"
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

  tags = {
    Name        = "services-api-${var.environment}"
    Environment = var.environment
  }
}



resource "aws_dynamodb_table" "appointments_table" {
  name           = "appointments-${var.environment}"
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

  tags = {
    Name        = "services-api-${var.environment}"
    Environment = var.environment
  }
}

# IAM Policy for DynamoDB access
resource "aws_iam_policy" "lambda_dynamodb_policy" {
  name        = "lambda_dynamodb_policy_${var.environment}"
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
          "cognito-idp:AdminUpdateUserAttributes",
          "cognito-idp:AdminGetUser",
          "cognito-idp:GetUser",
          "cognito-idp:GetGroup",
          "cognito-idp:CreateGroup",
          "cognito-idp:ListUsers",
          "cognito-idp:ListGroups"
        ]
        Effect   = "Allow"
        Resource = var.cognito_user_pool_arn
      }
    ]
  })
}