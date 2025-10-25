# ============================================
# Terraform Variables
# ============================================

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "mcp-server"
}

variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

# ============================================
# Networking
# ============================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# ============================================
# Database
# ============================================

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "mcpdb"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "mcpuser"
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

# ============================================
# Redis
# ============================================

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

# ============================================
# ECS
# ============================================

variable "ecs_task_cpu" {
  description = "ECS task CPU units"
  type        = string
  default     = "512"
}

variable "ecs_task_memory" {
  description = "ECS task memory (MiB)"
  type        = string
  default     = "1024"
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

# ============================================
# Application
# ============================================

variable "app_image" {
  description = "Docker image for the application"
  type        = string
  default     = "mcp-server:latest"
}

variable "app_port" {
  description = "Application port"
  type        = number
  default     = 8000
}

# ============================================
# Tags
# ============================================

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project   = "MCP Server"
    ManagedBy = "Terraform"
  }
}
