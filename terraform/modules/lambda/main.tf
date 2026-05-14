resource "aws_iam_policy" "lambda_ses_policy" {
  name        = "${var.environment}-lambda-ses-policy"
  description = "IAM policy for Lambda to send emails via SES"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ],
        Resource = "*"
      }
    ]
  })
}

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
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Resource = [
          var.users_table_arn,
          "${var.users_table_arn}/index/*",
          var.clinics_table_arn,
          "${var.clinics_table_arn}/index/*",
          var.availability_table_arn,
          "${var.availability_table_arn}/index/*",
          var.appointments_table_arn,
          "${var.appointments_table_arn}/index/*",
          var.medical_records_table_arn,
          var.medical_record_notes_table_arn,
          "${var.medical_record_notes_table_arn}/index/*"
        ]
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
          "cognito-idp:AdminRemoveUserFromGroup",
          "cognito-idp:GetGroup",
          "cognito-idp:ListGroups",
          "cognito-idp:CreateGroup",
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

resource "aws_iam_role_policy_attachment" "lambda_ses_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_ses_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_cloudwatch_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_cloudwatch_policy.arn
}


resource "aws_iam_policy" "lambda_kms_policy" {
  name        = "${var.environment}-lambda-kms-policy"
  description = "Allow Lambda to use KMS key for env vars decryption"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:DescribeKey"
        ],
        Resource = "arn:aws:kms:us-east-1:640168409035:key/f3f487ac-0df3-465d-947c-2d45c5272e1d"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_kms_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_kms_policy.arn
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
      USERS_TABLE        = var.users_table_name
      USER_CLINIC_ADSCRIPTION_TABLE = var.user_clinic_adscription_table_name
      ENVIRONMENT        = var.environment
      USER_POOL_ID       = var.cognito_user_pool_id
      SES_FROM_EMAIL     = var.ses_from_email
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecr_repository" "whatsapp_webhook" {
  name                 = "${var.project_name}-whatsapp-webhook-${var.environment}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecr_repository_policy" "whatsapp_webhook" {
  repository = aws_ecr_repository.whatsapp_webhook.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaECRAccess"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
      }
    ]
  })
}

resource "aws_lambda_function" "whatsapp_webhook" {
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.whatsapp_webhook.repository_url}:latest"
  function_name = "whatsapp-webhook-${var.environment}"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 300
  memory_size   = 1024

  environment {
    variables = {
      ENVIRONMENT              = var.environment
      WHATSAPP_VERIFY_TOKEN    = var.whatsapp_verify_token
      WHATSAPP_API_TOKEN       = var.whatsapp_api_token
      WHATSAPP_PHONE_NUMBER_ID = var.whatsapp_phone_number_id
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lambda_function" "availability_crud" {
  filename         = var.availability_lambda_zip_path
  source_code_hash = filebase64sha256(var.availability_lambda_zip_path)
  function_name    = "availability-crud-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "availability_function.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      AVAILABILITY_TABLE = var.availability_table_name
      USER_POOL_ID       = var.cognito_user_pool_id
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lambda_function" "email_sender" {
  filename         = var.email_lambda_zip_path
  source_code_hash = filebase64sha256(var.email_lambda_zip_path)
  function_name    = "email-sender-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "email_function.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      ENVIRONMENT    = var.environment
      SES_FROM_EMAIL = var.ses_from_email
      SES_TO_EMAIL   = var.ses_to_email
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lambda_function" "appointments_crud" {
  filename         = var.appointments_lambda_zip_path
  source_code_hash = filebase64sha256(var.appointments_lambda_zip_path)
  function_name    = "appointments-crud-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "appointments_function.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      APPOINTMENTS_TABLE = var.appointments_table_name
      AVAILABILITY_TABLE = var.availability_table_name
      USER_POOL_ID       = var.cognito_user_pool_id
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lambda_function" "medical_records_crud" {
  filename         = var.medical_records_lambda_zip_path
  source_code_hash = filebase64sha256(var.medical_records_lambda_zip_path)
  function_name    = "medical-records-crud-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "medical_records_function.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      ENVIRONMENT                  = var.environment
      MEDICAL_RECORDS_TABLE        = var.medical_records_table_name
      MEDICAL_RECORD_NOTES_TABLE   = var.medical_record_notes_table_name
      USER_POOL_ID                 = var.cognito_user_pool_id
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
      CLINICS_TABLE      = var.clinics_table_name
      USER_CLINIC_ADSCRIPTION_TABLE = var.user_clinic_adscription_table_name
      ENVIRONMENT        = var.environment
      USER_POOL_ID       = var.cognito_user_pool_id
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}