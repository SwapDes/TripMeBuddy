# Trip Me Buddy - ECS Task Definition & Service
# Optimized for Free Tier (Public Subnets, No NAT Gateway)

# 1. Task Definition
resource "aws_ecs_task_definition" "keycloak" {
  family                   = "${var.project_name}-keycloak-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"  # 0.5 vCPU (Free tier friendly)
  memory                   = "1024" # 1 GB Memory

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "keycloak"
      image     = "${aws_ecr_repository.keycloak.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8080
          hostPort      = 8080
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "KC_DB", value = "postgres" },
        { name = "KC_DB_URL", value = "jdbc:postgresql://${aws_db_instance.postgres.endpoint}/${aws_db_instance.postgres.db_name}" },
        { name = "KC_DB_USERNAME", value = var.db_username },
        { name = "KC_DB_PASSWORD", value = var.db_password },
        { name = "KC_HOSTNAME", value = aws_lb.main.dns_name },
        { name = "KC_PROXY_HEADERS", value = "xforwarded" },
        # UPDATED LINES BELOW
        { name = "KEYCLOAK_ADMIN", value = var.keycloak_admin_user },
        { name = "KEYCLOAK_ADMIN_PASSWORD", value = var.keycloak_admin_password }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "keycloak"
        }
      }
    }
  ])

  tags = {
    Name        = "${var.project_name}-keycloak-task"
    Project     = var.project_name
    Environment = var.environment
  }
}

# 2. ECS Service
resource "aws_ecs_service" "keycloak" {
  name            = "${var.project_name}-keycloak-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.keycloak.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  # NETWORK CONFIGURATION (CRITICAL FOR COST SAVINGS)
  # Assign public IP so it can reach internet without NAT Gateway
  network_configuration {
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    security_groups  = [aws_security_group.keycloak.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.keycloak.arn
    container_name   = "keycloak"
    container_port   = 8080
  }

  tags = {
    Name        = "${var.project_name}-keycloak-service"
    Project     = var.project_name
    Environment = var.environment
  }
}

# 3. ALB Target Group
resource "aws_lb_target_group" "keycloak" {
  name        = "${var.project_name}-keycloak-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 60
    interval            = 300
    matcher             = "200-399"
  }

  tags = {
    Name        = "${var.project_name}-keycloak-tg"
    Project     = var.project_name
    Environment = var.environment
  }
}

# 4. Update ALB Listener to forward to Keycloak
resource "aws_lb_listener_rule" "keycloak" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.keycloak.arn
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }
}
