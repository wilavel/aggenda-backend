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