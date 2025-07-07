resource "aws_iam_role" "lambda_role" {
  name = "${var.environment}-lambda-role"

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

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_policy" "lambda_dynamodb_policy" {
  name        = "${var.environment}-lambda-dynamodb-policy"
  description = "IAM policy for Lambda to access DynamoDB"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = var.dynamodb_table_arn
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_cognito_policy" {
  name        = "${var.environment}-lambda-cognito-policy"
  description = "IAM policy for Lambda to access Cognito"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminSetUserPassword",
          "cognito-idp:AdminUpdateUserAttributes",
          "cognito-idp:AdminDeleteUser",
          "cognito-idp:AdminListGroupsForUser",
          "cognito-idp:GetGroup",
          "cognito-idp:AdminAddUserToGroup"
        ]
        Effect   = "Allow"
        Resource = var.cognito_user_pool_arn
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_cloudwatch_policy" {
  name        = "${var.environment}-lambda-cloudwatch-policy"
  description = "IAM policy for Lambda to write logs to CloudWatch"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_dynamodb_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_cognito_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_cognito_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_cloudwatch_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_cloudwatch_policy.arn
}

resource "aws_lambda_function" "users_crud" {
  filename         = var.users_lambda_zip_path
  source_code_hash = filebase64sha256(var.users_lambda_zip_path)
  function_name    = "users-crud-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "users_function.lambda_handler"
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  environment {
    variables = {
      USERS_TABLE        = var.dynamodb_table_name
      ENVIRONMENT        = var.environment
      USER_POOL_ID       = var.cognito_user_pool_id
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lambda_function" "clinics_crud" {
  filename         = var.clinics_lambda_zip_path
  source_code_hash = filebase64sha256(var.clinics_lambda_zip_path)
  function_name    = "clinics-crud-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "clinics_function.lambda_handler"
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  environment {
    variables = {
      CLINICS_TABLE      = var.dynamodb_table_name
      ENVIRONMENT        = var.environment
      USER_POOL_ID       = var.cognito_user_pool_id
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
} 