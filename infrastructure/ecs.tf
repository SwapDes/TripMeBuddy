# ==============================================================================
# Trip Me Buddy — Keycloak ECS Resources
# ==============================================================================
# KC_PROXY=edge     — tells Keycloak it sits behind an HTTPS-terminating ALB.
#                     Enables Secure flag on cookies; required to prevent
#                     cross-origin POST failures (signup/login) on modern browsers.
# KC_PROXY_HEADERS  — instructs Keycloak to read X-Forwarded-* headers from ALB
#                     for correct host and scheme detection.
# KC_HOSTNAME       — public hostname presented to clients in redirects and tokens.
# KC_HOSTNAME_STRICT / KC_HOSTNAME_STRICT_HTTPS = false — allows Keycloak to
#                     respond on internal HTTP while presenting HTTPS hostname externally.
# KC_HTTP_ENABLED   — required because ALB terminates TLS and connects to the
#                     container over HTTP internally.
# ==============================================================================

resource "aws_ecr_repository" "keycloak" {
  name                 = "${var.project_name}-keycloak"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.project_name}-keycloak-repo"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_lb_target_group" "keycloak" {
  name        = "${var.project_name}-keycloak-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/realms/master"
    matcher             = "200-399"
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 60
    interval            = 300
  }

  tags = {
    Name        = "${var.project_name}-keycloak-tg"
    Project     = var.project_name
    Environment = var.environment
  }
}

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

resource "aws_ecs_task_definition" "keycloak" {
  family                   = "${var.project_name}-keycloak-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

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
          name          = "keycloak-8080-tcp"
        }
      ]

      environment = [
        # Proxy — required for correct HTTPS cookie behaviour behind ALB
        { name = "KC_PROXY",                 value = "edge" },
        { name = "KC_PROXY_HEADERS",         value = "xforwarded" },

        # Hostname — must match the public domain, not the internal ALB DNS
        { name = "KC_HOSTNAME",              value = "api.senseddreams.com" },
        { name = "KC_HOSTNAME_STRICT",       value = "false" },
        { name = "KC_HOSTNAME_STRICT_HTTPS", value = "false" },

        # HTTP must be enabled — ALB terminates HTTPS and reaches container over HTTP
        { name = "KC_HTTP_ENABLED",          value = "true" },

        # Database
        { name = "KC_DB",          value = "postgres" },
        { name = "KC_DB_USERNAME", value = "postgres" },
        { name = "KC_DB_URL",      value = "jdbc:postgresql://${aws_db_instance.postgres.address}:5432/${aws_db_instance.postgres.db_name}" },

        # Admin user
        { name = "KEYCLOAK_ADMIN", value = "admin" },
      ]

      # Sensitive values pulled from SSM at container start — never stored as plaintext
      secrets = [
        {
          name      = "KC_DB_PASSWORD"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/trip-me-buddy/keycloak-db-password"
        },
        {
          name      = "KEYCLOAK_ADMIN_PASSWORD"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/trip-me-buddy/keycloak-admin-password"
        }
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

resource "aws_ecs_service" "keycloak" {
  name            = "${var.project_name}-keycloak-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.keycloak.arn
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
    security_groups  = [aws_security_group.keycloak.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.keycloak.arn
    container_name   = "keycloak"
    container_port   = 8080
  }

  depends_on = [aws_lb_listener.http, aws_lb_listener_rule.keycloak]

  tags = {
    Name        = "${var.project_name}-keycloak-service"
    Project     = var.project_name
    Environment = var.environment
  }
}
