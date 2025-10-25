# ============================================
# Terraform Outputs
# ============================================

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.mcp_vpc.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.mcp.endpoint
  sensitive   = true
}

output "rds_connection_string" {
  description = "RDS connection string (without password)"
  value       = "postgresql://${var.db_username}:PASSWORD@${aws_db_instance.mcp.endpoint}/${var.db_name}"
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.mcp.cache_nodes[0].address
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = aws_elasticache_cluster.mcp.cache_nodes[0].port
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = "redis://${aws_elasticache_cluster.mcp.cache_nodes[0].address}:${aws_elasticache_cluster.mcp.cache_nodes[0].port}/0"
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.mcp.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.mcp.arn
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.mcp.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN"
  value       = aws_ecr_repository.mcp.arn
}

output "s3_bucket_name" {
  description = "S3 bucket name for data storage"
  value       = aws_s3_bucket.mcp_data.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.mcp_data.arn
}

# ============================================
# Environment Variables for Application
# ============================================

output "environment_variables" {
  description = "Environment variables to configure in ECS task"
  value = {
    DATABASE_URL = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.mcp.endpoint}/${var.db_name}"
    REDIS_URL    = "redis://${aws_elasticache_cluster.mcp.cache_nodes[0].address}:${aws_elasticache_cluster.mcp.cache_nodes[0].port}/0"
    ENVIRONMENT  = var.environment
    AWS_REGION   = var.aws_region
    S3_BUCKET_NAME = aws_s3_bucket.mcp_data.id
  }
  sensitive = true
}
