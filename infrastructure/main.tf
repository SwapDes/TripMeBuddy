# ==============================================================================
# Trip Me Buddy — Terraform Infrastructure
# ==============================================================================
# Cost control: set services_running=false to scale all ECS services to 0.
# RDS has no Terraform stop equivalent — use CLI when not needed:
#   Stop:  aws rds stop-db-instance --db-instance-identifier trip-me-buddy-postgres --region us-east-1
#   Start: aws rds start-db-instance --db-instance-identifier trip-me-buddy-postgres --region us-east-1
# ElastiCache cannot be stopped — it must be destroyed and recreated (cheap at cache.t3.micro).
# ==============================================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ==============================================================================
# VARIABLES
# ==============================================================================

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used as prefix on all resource names and tags"
  type        = string
  default     = "trip-me-buddy"
}

variable "environment" {
  description = "Environment tag applied to all resources"
  type        = string
  default     = "dev"
}

variable "services_running" {
  description = <<-EOT
    Controls whether ECS services are running.
    true  = desired_count 1 (normal operation)
    false = desired_count 0 (cost saving mode — containers stopped, config preserved)
    Usage: terraform apply -var="services_running=false"
  EOT
  type    = bool
  default = true
}

# ==============================================================================
# DATA SOURCES
# ==============================================================================

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

# ==============================================================================
# NETWORKING
# ==============================================================================

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-igw"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Public subnets — ECS tasks run here with assign_public_ip=true to avoid NAT Gateway cost
resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.project_name}-public-subnet-1"
    Project     = var.project_name
    Environment = var.environment
    Type        = "Public"
  }
}

resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.project_name}-public-subnet-2"
    Project     = var.project_name
    Environment = var.environment
    Type        = "Public"
  }
}

# Private subnets — RDS and ElastiCache live here
resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name        = "${var.project_name}-private-subnet-1"
    Project     = var.project_name
    Environment = var.environment
    Type        = "Private"
  }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name        = "${var.project_name}-private-subnet-2"
    Project     = var.project_name
    Environment = var.environment
    Type        = "Private"
  }
}

# ==============================================================================
# NAT GATEWAY — COMMENTED OUT (saves ~$32/month)
# ECS tasks use public subnets with assign_public_ip=true instead.
# NOTE: A NAT Gateway (nat-0adcfa5de722d437d) was manually added to the private
# route table via CLI/Console and is not managed by Terraform. If it is removed,
# private subnets lose outbound internet access (RDS/Redis are not affected as
# they only need inbound connections from ECS tasks).
# To bring NAT Gateway under Terraform management, uncomment these blocks and
# add nat_gateway_id to the private route table route block.
# ==============================================================================

# resource "aws_eip" "nat" {
#   domain     = "vpc"
#   depends_on = [aws_internet_gateway.main]
#   tags = {
#     Name        = "${var.project_name}-nat-eip"
#     Project     = var.project_name
#     Environment = var.environment
#   }
# }

# resource "aws_nat_gateway" "main" {
#   allocation_id = aws_eip.nat.id
#   subnet_id     = aws_subnet.public_1.id
#   depends_on    = [aws_internet_gateway.main]
#   tags = {
#     Name        = "${var.project_name}-nat"
#     Project     = var.project_name
#     Environment = var.environment
#   }
# }

# ==============================================================================
# ROUTE TABLES
# ==============================================================================

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name        = "${var.project_name}-public-rt"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  # No route defined here — NAT Gateway route was manually added (see note above).
  # If NAT is uncommented above, add:
  # route {
  #   cidr_block     = "0.0.0.0/0"
  #   nat_gateway_id = aws_nat_gateway.main.id
  # }

  tags = {
    Name        = "${var.project_name}-private-rt"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_1.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_2.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private_1" {
  subnet_id      = aws_subnet.private_1.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_2" {
  subnet_id      = aws_subnet.private_2.id
  route_table_id = aws_route_table.private.id
}

# ==============================================================================
# SECURITY GROUPS
# ==============================================================================

resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-alb-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_security_group" "keycloak" {
  name        = "${var.project_name}-keycloak-sg"
  description = "Security group for Keycloak ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Keycloak from ALB"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-keycloak-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_security_group" "backend" {
  name        = "${var.project_name}-backend-sg"
  description = "Security group for Backend ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Backend from ALB"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-backend-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "PostgreSQL from private and public subnets"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [
      aws_subnet.private_1.cidr_block,
      aws_subnet.private_2.cidr_block,
      aws_subnet.public_1.cidr_block,
      aws_subnet.public_2.cidr_block,
    ]
  }

  ingress {
    description     = "PostgreSQL from backend ECS security group"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-rds-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_security_group" "redis" {
  name        = "${var.project_name}-redis-sg"
  description = "Security group for Redis ElastiCache"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Redis from private and public subnets"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [
      aws_subnet.private_1.cidr_block,
      aws_subnet.private_2.cidr_block,
      aws_subnet.public_1.cidr_block,
      aws_subnet.public_2.cidr_block,
    ]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-redis-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

# ==============================================================================
# DATABASES
# ==============================================================================

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]

  tags = {
    Name        = "${var.project_name}-db-subnet-group"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_db_instance" "postgres" {
  identifier     = "${var.project_name}-postgres"
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "tripmebbuddy_v2"
  username = "postgres"
  # Password is not stored in Terraform. Set it on first apply then rotate via
  # AWS Console. The ignore_changes lifecycle below ensures Terraform never
  # attempts to change or expose the password after initial creation.
  password = "SET_ON_FIRST_APPLY_ONLY"

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az                = false
  publicly_accessible     = false
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  skip_final_snapshot       = true
  final_snapshot_identifier = "${var.project_name}-final-snapshot"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  lifecycle {
    ignore_changes = [
      engine_version, # AWS patches minor versions automatically
      password,       # Managed outside Terraform after initial creation
    ]
  }

  tags = {
    Name        = "${var.project_name}-postgres"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]

  tags = {
    Name        = "${var.project_name}-redis-subnet-group"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project_name}-redis"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  snapshot_retention_limit = 0
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "mon:05:00-mon:07:00"

  lifecycle {
    ignore_changes = [engine_version]
  }

  tags = {
    Name        = "${var.project_name}-redis"
    Project     = var.project_name
    Environment = var.environment
  }
}

# ==============================================================================
# IAM
# ==============================================================================

resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_ssm_policy" {
  name = "${var.project_name}-ecs-ssm-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameters", "ssm:GetParameter"]
      Resource = ["arn:aws:ssm:us-east-1:*:parameter/trip-me-buddy/*"]
    }]
  })
}

# ==============================================================================
# APPLICATION LOAD BALANCER
# ==============================================================================

resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public_1.id, aws_subnet.public_2.id]
  idle_timeout       = 300

  tags = {
    Name        = "${var.project_name}-alb"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "404: Not Found"
      status_code  = "404"
    }
  }
}

# ==============================================================================
# ECS CLUSTER & CLOUDWATCH
# ==============================================================================

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "${var.project_name}-cluster"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-logs"
    Project     = var.project_name
    Environment = var.environment
  }
}

# ==============================================================================
# OUTPUTS
# ==============================================================================

output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = [aws_subnet.public_1.id, aws_subnet.public_2.id]
}

output "private_subnet_ids" {
  value = [aws_subnet.private_1.id, aws_subnet.private_2.id]
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "rds_endpoint" {
  value     = aws_db_instance.postgres.endpoint
  sensitive = true
}

output "rds_database_name" {
  value = aws_db_instance.postgres.db_name
}

output "redis_endpoint" {
  value     = aws_elasticache_cluster.redis.cache_nodes[0].address
  sensitive = true
}

output "redis_port" {
  value = aws_elasticache_cluster.redis.port
}

output "security_group_ids" {
  value = {
    alb      = aws_security_group.alb.id
    backend  = aws_security_group.backend.id
    keycloak = aws_security_group.keycloak.id
    rds      = aws_security_group.rds.id
    redis    = aws_security_group.redis.id
  }
}

output "ecr_repository_url" {
  description = "ECR Repository URL for Keycloak"
  value       = aws_ecr_repository.keycloak.repository_url
}

output "backend_ecr_repository_url" {
  description = "ECR Repository URL for Backend"
  value       = aws_ecr_repository.backend.repository_url
}

output "backend_service_name" {
  value = aws_ecs_service.backend.name
}
