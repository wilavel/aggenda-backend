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