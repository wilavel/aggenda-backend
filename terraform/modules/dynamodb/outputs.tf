output "table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.users_table.name
}

output "table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.users_table.arn
} 

output "clinics_table_name" {
  value = aws_dynamodb_table.clinics_table.name
}

output "clinics_table_arn" {
  value = aws_dynamodb_table.clinics_table.arn
}


output "appointments_table_name" {
  value = aws_dynamodb_table.appointments_table.name
}

output "appointments_table_arn" {
  value       = aws_dynamodb_table.appointments_table.arn
}

output "user_clinic_adscription_table_name" {
  value = aws_dynamodb_table.user_clinic_adscription.name
}

output "user_clinic_adscription_table_arn" {
  value = aws_dynamodb_table.user_clinic_adscription.arn
}

output "doctor_availability_table_name" {
  value = aws_dynamodb_table.doctor_availability.name
}

output "doctor_availability_table_arn" {
  value = aws_dynamodb_table.doctor_availability.arn
}

output "medical_records_table_name" {
  value = aws_dynamodb_table.medical_records.name
}

output "medical_records_table_arn" {
  value = aws_dynamodb_table.medical_records.arn
}

output "medical_record_notes_table_name" {
  value = aws_dynamodb_table.medical_record_notes.name
}

output "medical_record_notes_table_arn" {
  value = aws_dynamodb_table.medical_record_notes.arn
}