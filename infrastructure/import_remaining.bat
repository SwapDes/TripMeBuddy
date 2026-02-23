@echo off
REM import_remaining.bat
REM Imports only the resources not yet in Terraform state.
REM Run from the infrastructure/ folder after filling in all placeholders.

cd /d "%~dp0"

echo === Importing remaining resources ===

terraform import aws_internet_gateway.main igw-018ea6836318aa72b

terraform import aws_subnet.public_1  subnet-0599159e1c0b3d7d4
terraform import aws_subnet.public_2  subnet-02aa02032cba0a367
terraform import aws_subnet.private_1 subnet-0a6195abe65dceac9
terraform import aws_subnet.private_2 subnet-04e47c497ae6a8a74

terraform import aws_route_table.public  rtb-090da10e17ae63e5b
terraform import aws_route_table.private rtb-07fb5992e6c42ec39

terraform import aws_route_table_association.public_1  subnet-0599159e1c0b3d7d4/rtb-090da10e17ae63e5b
terraform import aws_route_table_association.public_2  subnet-02aa02032cba0a367/rtb-090da10e17ae63e5b
terraform import aws_route_table_association.private_1 subnet-0a6195abe65dceac9/rtb-07fb5992e6c42ec39
terraform import aws_route_table_association.private_2 subnet-04e47c497ae6a8a74/rtb-07fb5992e6c42ec39

terraform import aws_security_group.alb      sg-03ab4f653887e5767
terraform import aws_security_group.backend  sg-06869af3322877e4d
terraform import aws_security_group.keycloak sg-066d460ea3ffeb970
terraform import aws_security_group.rds      sg-0d6304e347e3487fc
terraform import aws_security_group.redis    sg-06bd840337fc98da0

terraform import aws_db_subnet_group.main         trip-me-buddy-db-subnet-group
terraform import aws_elasticache_subnet_group.main trip-me-buddy-redis-subnet-group

terraform import aws_ecr_repository.backend  trip-me-buddy-backend
terraform import aws_ecr_repository.keycloak trip-me-buddy-keycloak

terraform import aws_iam_role.ecs_task_execution_role trip-me-buddy-ecs-task-execution-role
terraform import aws_iam_role_policy.ecs_ssm_policy trip-me-buddy-ecs-task-execution-role:trip-me-buddy-ecs-ssm-policy
terraform import aws_iam_role_policy_attachment.ecs_task_execution_role_policy trip-me-buddy-ecs-task-execution-role/arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

terraform import aws_lb.main             arn:aws:elasticloadbalancing:us-east-1:594585418788:loadbalancer/app/trip-me-buddy-alb/9a0fdaa259c20e8c
terraform import aws_lb_listener.http    arn:aws:elasticloadbalancing:us-east-1:594585418788:listener/app/trip-me-buddy-alb/9a0fdaa259c20e8c/56e4f1628508ff7d
terraform import aws_lb_listener_rule.backend  arn:aws:elasticloadbalancing:us-east-1:594585418788:listener-rule/app/trip-me-buddy-alb/9a0fdaa259c20e8c/56e4f1628508ff7d/5e98057f54a457e6
terraform import aws_lb_listener_rule.keycloak arn:aws:elasticloadbalancing:us-east-1:594585418788:listener-rule/app/trip-me-buddy-alb/9a0fdaa259c20e8c/56e4f1628508ff7d/a49f9560ce272f63
terraform import aws_lb_target_group.backend  arn:aws:elasticloadbalancing:us-east-1:594585418788:targetgroup/trip-me-buddy-backend-tg/43aae11a2f0c5d89
terraform import aws_lb_target_group.keycloak arn:aws:elasticloadbalancing:us-east-1:594585418788:targetgroup/trip-me-buddy-keycloak-tg/24cbe783d3840452

terraform import aws_ecs_cluster.main trip-me-buddy-cluster

echo.
echo === Done. Run plan_and_mask.bat to verify. ===
pause
