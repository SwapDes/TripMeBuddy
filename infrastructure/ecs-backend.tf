# ==============================================================================
# Trip Me Buddy — Backend ECS Resources
# ==============================================================================

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
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

resource "aws_lb_target_group" "backend" {
  name        = "${var.project_name}-backend-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/health"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  tags = {
    Name        = "${var.project_name}-backend-tg"
    Project     = var.project_name
    Environment = var.environment
  }
}

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

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-backend-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = "${aws_ecr_repository.backend.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        # Application
        { name = "PROJECT_NAME", value = "Trip Me Buddy API" },
        { name = "VERSION",      value = "1.0.0" },
        { name = "DEBUG",        value = "False" },

        # Database (credentials injected via SSM secrets below)
        { name = "DB_HOST", value = aws_db_instance.postgres.address },
        { name = "DB_PORT", value = "5432" },
        { name = "DB_NAME", value = aws_db_instance.postgres.db_name },

        # Redis (no auth on this cluster)
        { name = "REDIS_HOST",     value = aws_elasticache_cluster.redis.cache_nodes[0].address },
        { name = "REDIS_PORT",     value = "6379" },
        { name = "REDIS_DB",       value = "0" },
        { name = "REDIS_PASSWORD", value = "" },

        # Keycloak — backend communicates via internal ALB HTTP endpoint
        { name = "KEYCLOAK_SERVER_URL",            value = "http://${aws_lb.main.dns_name}" },
        { name = "KEYCLOAK_REALM",                 value = "tripmebuddy" },
        { name = "KEYCLOAK_CLIENT_ID",             value = "trip-me-buddy-frontend" },
        { name = "KEYCLOAK_BACKEND_CLIENT_ID",     value = "trip-me-buddy-backend" },
        # Backend client secret comes from SSM below; this env var is intentionally blank
        { name = "KEYCLOAK_BACKEND_CLIENT_SECRET", value = "" },
        { name = "ALGORITHM",                      value = "RS256" },

        # CORS — includes both local dev and production domains
        { name = "BACKEND_CORS_ORIGINS", value = jsonencode([
          "http://localhost:5173",
          "http://localhost:3000",
          "https://tripmebuddy.senseddreams.com",
          "https://senseddreams.com"
        ]) },
      ]

      # Sensitive values pulled from SSM at container start — never stored as plaintext
      secrets = [
        {
          name      = "DB_USER"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/trip-me-buddy/db-user"
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/trip-me-buddy/db-password"
        },
        {
          name      = "KEYCLOAK_CLIENT_SECRET"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/trip-me-buddy/keycloak-client-secret"
        },
        {
          name      = "AMADEUS_API_KEY"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/trip-me-buddy/amadeus-api-key"
        },
        {
          name      = "AMADEUS_API_SECRET"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/trip-me-buddy/amadeus-api-secret"
        },
        {
          name      = "GEMINI_API_KEY"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/trip-me-buddy/gemini-api-key"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name        = "${var.project_name}-backend-task"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-backend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  launch_type     = "FARGATE"

  # services_running=false sets this to 0 (cost saving mode)
  # services_running=true  sets this to 1 (normal operation)
  desired_count = var.services_running ? 1 : 0

  # CI/CD deploys new image tags by calling ecs update-service directly.
  # Terraform manages configuration; ignore the running task revision.
  lifecycle {
    ignore_changes = [task_definition]
  }

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

  depends_on = [aws_lb_listener.http, aws_lb_listener_rule.backend]

  tags = {
    Name        = "${var.project_name}-backend-service"
    Project     = var.project_name
    Environment = var.environment
  }
}
