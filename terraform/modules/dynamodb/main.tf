resource "aws_dynamodb_table" "users_table" {
  name           = "${var.environment}-users"
  billing_mode   = var.billing_mode
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Name        = "${var.environment}-users-table"
    Environment = var.environment
    Project     = var.project_name
  }
} 

# Tabla para clínicas
resource "aws_dynamodb_table" "clinics_table" {
  name           = "${var.environment}-clinics"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Tabla para relación usuarios-clínicas
resource "aws_dynamodb_table" "user_clinics_table" {
  name           = "${var.environment}-user-clinics"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  range_key      = "clinic_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "clinic_id"
    type = "S"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Tabla para citas
resource "aws_dynamodb_table" "appointments_table" {
  name           = "${var.environment}-appointments"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"
  range_key      = "clinic_id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "clinic_id"
    type = "S"
  }

  attribute {
    name = "patient_id"
    type = "S"
  }

  attribute {
    name = "doctor_id"
    type = "S"
  }

  attribute {
    name = "appointment_date"
    type = "S"
  }

  global_secondary_index {
    name               = "PatientIdIndex"
    hash_key           = "patient_id"
    range_key          = "appointment_date"
    projection_type    = "ALL"
  }

  global_secondary_index {
    name               = "DoctorIdIndex"
    hash_key           = "doctor_id"
    range_key          = "appointment_date"
    projection_type    = "ALL"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
} 