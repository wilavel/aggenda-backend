variable "function_name" {
  description = "Nombre de la función Lambda"
  type        = string
}

variable "source_code_path" {
  description = "Ruta al código fuente"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "ARN de la tabla DynamoDB"
  type        = string
}