variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "callback_urls" {
  description = "List of allowed callback URLs for the user pool client"
  type        = list(string)
  default     = ["http://localhost:3000"]
}

variable "logout_urls" {
  description = "List of allowed logout URLs for the user pool client"
  type        = list(string)
  default     = ["http://localhost:3000"]
}

variable "existing_user_pool_id" {
  description = "ID of an existing Cognito User Pool to use instead of creating a new one"
  type        = string
}

variable "existing_client_id" {
  description = "ID of an existing Cognito User Pool Client to use instead of creating a new one"
  type        = string
}