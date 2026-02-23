@echo off
REM ==============================================================================
REM TripMeBuddy - Terraform State Import
REM ==============================================================================
REM INSTRUCTIONS:
REM 1. Run each AWS CLI command in the "HOW TO FIND EACH VALUE" section below
REM    in your terminal to get the actual IDs
REM 2. Replace every REPLACE_WITH_... placeholder in the IMPORTS section with
REM    the value you retrieved
REM 3. Save the file and double-click it, or run it from the infrastructure/ folder
REM
REM Safe to run multiple times. Already-imported resources will show an error
REM for that line and continue — this does not affect AWS resources.
REM ==============================================================================

REM HOW TO FIND EACH VALUE — run these in PowerShell, copy the output:
REM
REM VPC ID:
REM   aws ec2 describe-vpcs --filters "Name=tag:Project,Values=trip-me-buddy" --region us-east-1 --query "Vpcs[0].VpcId" --output text
REM
REM Internet Gateway ID:
REM   aws ec2 describe-internet-gateways --filters "Name=tag:Project,Values=trip-me-buddy" --region us-east-1 --query "InternetGateways[0].InternetGatewayId" --output text
REM
REM Subnet IDs (run this and match by Name column):
REM   aws ec2 describe-subnets --filters "Name=tag:Project,Values=trip-me-buddy" --region us-east-1 --query "Subnets[*].{id:SubnetId,name:Tags[?Key=='Name']|[0].Value}" --output table
REM
REM Route Table IDs (match by Name column, also shows RouteTableAssociationId per subnet):
REM   aws ec2 describe-route-tables --filters "Name=tag:Project,Values=trip-me-buddy" --region us-east-1 --query "RouteTables[*].{id:RouteTableId,name:Tags[?Key=='Name']|[0].Value,assocs:Associations[*].{assocId:RouteTableAssociationId,subnetId:SubnetId}}" --output json
REM
REM Security Group IDs (match by GroupName column):
REM   aws ec2 describe-security-groups --filters "Name=tag:Project,Values=trip-me-buddy" --region us-east-1 --query "SecurityGroups[*].{id:GroupId,name:GroupName}" --output table
REM
REM ALB ARN:
REM   aws elbv2 describe-load-balancers --names trip-me-buddy-alb --region us-east-1 --query "LoadBalancers[0].LoadBalancerArn" --output text
REM
REM Listener ARN (replace ALB_ARN with value from above):
REM   aws elbv2 describe-listeners --load-balancer-arn ALB_ARN --region us-east-1 --query "Listeners[?Port=='80'].ListenerArn|[0]" --output text
REM
REM Listener Rule ARNs (replace LISTENER_ARN with value from above):
REM   aws elbv2 describe-rules --listener-arn LISTENER_ARN --region us-east-1 --query "Rules[?Priority!='default'].{arn:RuleArn,priority:Priority}" --output table
REM
REM Backend Target Group ARN:
REM   aws elbv2 describe-target-groups --names trip-me-buddy-backend-tg --region us-east-1 --query "TargetGroups[0].TargetGroupArn" --output text
REM
REM Keycloak Target Group ARN:
REM   aws elbv2 describe-target-groups --names trip-me-buddy-keycloak-tg --region us-east-1 --query "TargetGroups[0].TargetGroupArn" --output text
REM
REM ECS Cluster ARN:
REM   aws ecs describe-clusters --clusters trip-me-buddy-cluster --region us-east-1 --query "clusters[0].clusterArn" --output text
REM ==============================================================================

cd /d "%~dp0"

echo === Starting Terraform state import ===

REM ── VPC ──────────────────────────────────────────────────────────────────────
terraform import aws_vpc.main vpc-0e9e6e42cd3136148

REM ── Internet Gateway ──────────────────────────────────────────────────────────
terraform import aws_internet_gateway.main igw-018ea6836318aa72b

REM ── Subnets ───────────────────────────────────────────────────────────────────
terraform import aws_subnet.public_1  subnet-0599159e1c0b3d7d4
terraform import aws_subnet.public_2  subnet-02aa02032cba0a367
terraform import aws_subnet.private_1 subnet-0a6195abe65dceac9
terraform import aws_subnet.private_2 subnet-04e47c497ae6a8a74

REM ── Route Tables ──────────────────────────────────────────────────────────────
terraform import aws_route_table.public  rtb-090da10e17ae63e5b
terraform import aws_route_table.private rtb-07fb5992e6c42ec39

REM ── Route Table Associations ──────────────────────────────────────────────────
REM Association ID format: the RouteTableAssociationId values from the route table query above
terraform import aws_route_table_association.public_1  rtbassoc-0b687e95c76c814d7
terraform import aws_route_table_association.public_2  rtbassoc-062d1256f10a01471
terraform import aws_route_table_association.private_1 rtbassoc-0fcabdb535e4ea195
terraform import aws_route_table_association.private_2 rtbassoc-0ef1671bad45da5b7

REM ── Security Groups ───────────────────────────────────────────────────────────
terraform import aws_security_group.alb      sg-03ab4f653887e5767
terraform import aws_security_group.backend  sg-06869af3322877e4d
terraform import aws_security_group.keycloak  sg-066d460ea3ffeb970
terraform import aws_security_group.rds      sg-0d6304e347e3487fc
terraform import aws_security_group.redis    sg-06bd840337fc98da0

REM ── DB Subnet Group ───────────────────────────────────────────────────────────
terraform import aws_db_subnet_group.main trip-me-buddy-db-subnet-group

REM ── ElastiCache Subnet Group ──────────────────────────────────────────────────
terraform import aws_elasticache_subnet_group.main trip-me-buddy-redis-subnet-group

REM ── ECR Repositories ──────────────────────────────────────────────────────────
terraform import aws_ecr_repository.backend  trip-me-buddy-backend
terraform import aws_ecr_repository.keycloak trip-me-buddy-keycloak

REM ── IAM ───────────────────────────────────────────────────────────────────────
terraform import aws_iam_role.ecs_task_execution_role trip-me-buddy-ecs-task-execution-role
terraform import aws_iam_role_policy.ecs_ssm_policy trip-me-buddy-ecs-task-execution-role:trip-me-buddy-ecs-ssm-policy
terraform import aws_iam_role_policy_attachment.ecs_task_execution_role_policy trip-me-buddy-ecs-task-execution-role/arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

REM ── ALB ───────────────────────────────────────────────────────────────────────
terraform import aws_lb.main arn:aws:elasticloadbalancing:us-east-1:594585418788:loadbalancer/app/trip-me-buddy-alb/9a0fdaa259c20e8c

REM ── ALB Listener ──────────────────────────────────────────────────────────────
terraform import aws_lb_listener.http arn:aws:elasticloadbalancing:us-east-1:594585418788:listener/app/trip-me-buddy-alb/9a0fdaa259c20e8c/56e4f1628508ff7d

REM ── ALB Listener Rules ────────────────────────────────────────────────────────
REM Priority 50 = backend rule, Priority 100 = keycloak rule
terraform import aws_lb_listener_rule.backend  arn:aws:elasticloadbalancing:us-east-1:594585418788:listener-rule/app/trip-me-buddy-alb/9a0fdaa259c20e8c/56e4f1628508ff7d/5e98057f54a457e6
terraform import aws_lb_listener_rule.keycloak arn:aws:elasticloadbalancing:us-east-1:594585418788:listener-rule/app/trip-me-buddy-alb/9a0fdaa259c20e8c/56e4f1628508ff7d/a49f9560ce272f63

REM ── Target Groups ─────────────────────────────────────────────────────────────
terraform import aws_lb_target_group.backend  arn:aws:elasticloadbalancing:us-east-1:594585418788:targetgroup/trip-me-buddy-backend-tg/43aae11a2f0c5d89
terraform import aws_lb_target_group.keycloak arn:aws:elasticloadbalancing:us-east-1:594585418788:targetgroup/trip-me-buddy-keycloak-tg/24cbe783d3840452

REM ── ECS Cluster ───────────────────────────────────────────────────────────────
terraform import aws_ecs_cluster.main arn:aws:ecs:us-east-1:594585418788:cluster/trip-me-buddy-cluster

REM ── CloudWatch Log Group ──────────────────────────────────────────────────────
terraform import aws_cloudwatch_log_group.ecs_logs /ecs/trip-me-buddy

echo.
echo === Import complete. Run: terraform plan ===
pause
