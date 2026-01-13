# ==============================================================================
# BACKEND ECS RESOURCES
# ==============================================================================

# Backend ECR Repository
resource "aws_ecr_repository" "backend" {
  name                 = "trip-me-buddy-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.project_name}-backend-repo"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Backend Target Group
resource "aws_lb_target_group" "backend" {
  name        = "${var.project_name}-backend-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name        = "${var.project_name}-backend-tg"
    Project     = var.project_name
    Environment = var.environment
  }
}

# ALB Listener Rule for Backend
resource "aws_lb_listener_rule" "backend" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 50

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/health", "/docs", "/redoc", "/openapi.json"]
    }
  }
}

# IAM Policy for ECS to access SSM Parameters
resource "aws_iam_role_policy" "ecs_ssm_policy" {
  name = "${var.project_name}-ecs-ssm-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:us-east-1:*:parameter/trip-me-buddy/*"
        ]
      }
    ]
  })
}

# ECS Task Definition for Backend
resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-backend-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = "backend"
      image = "${aws_ecr_repository.backend.repository_url}:latest"
      
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "PROJECT_NAME", value = "Trip Me Buddy API" },
        { name = "VERSION", value = "1.0.0" },
        { name = "DEBUG", value = "False" },
        { name = "DB_HOST", value = aws_db_instance.postgres.address },
        { name = "DB_PORT", value = "5432" },
        { name = "DB_NAME", value = aws_db_instance.postgres.db_name },
        { name = "REDIS_HOST", value = aws_elasticache_cluster.redis.cache_nodes[0].address },
        { name = "REDIS_PORT", value = "6379" },
        { name = "REDIS_DB", value = "0" },
        { name = "REDIS_PASSWORD", value = "" },
        { name = "KEYCLOAK_SERVER_URL", value = "http://${aws_lb.main.dns_name}" },
        { name = "KEYCLOAK_REALM", value = "tripmebuddy" },
        { name = "KEYCLOAK_CLIENT_ID", value = "trip-me-buddy-backend" },
        { name = "BACKEND_CORS_ORIGINS", value = "[\"http://localhost:3000\",\"http://localhost:5173\"]" },
        { name = "ALGORITHM", value = "RS256" }
      ]

      secrets = [
        {
          name      = "DB_USER"
          valueFrom = "arn:aws:ssm:us-east-1:594585418788:parameter/trip-me-buddy/db-user"
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = "arn:aws:ssm:us-east-1:594585418788:parameter/trip-me-buddy/db-password"
        },
        {
          name      = "KEYCLOAK_CLIENT_SECRET"
          valueFrom = "arn:aws:ssm:us-east-1:594585418788:parameter/trip-me-buddy/keycloak-client-secret"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "backend"
        }
      }
    }
  ])

  tags = {
    Name        = "${var.project_name}-backend-task"
    Project     = var.project_name
    Environment = var.environment
  }
}

# ECS Service for Backend
resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-backend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    security_groups  = [aws_security_group.backend.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  depends_on = [
    aws_lb_listener.http,
    aws_lb_listener_rule.backend
  ]

  tags = {
    Name        = "${var.project_name}-backend-service"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Outputs
output "backend_ecr_repository_url" {
  description = "ECR Repository URL for Backend"
  value       = aws_ecr_repository.backend.repository_url
}

output "backend_service_name" {
  description = "Backend ECS Service Name"
  value       = aws_ecs_service.backend.name
}
