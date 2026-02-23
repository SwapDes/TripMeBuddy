@echo off
REM ==============================================================================
REM TripMeBuddy - Terraform Plan + Mask
REM Run from the infrastructure/ folder.
REM Output: tfplan_masked.txt — safe to share for review.
REM ==============================================================================

cd /d "%~dp0"

echo === Generating Terraform plan ===
terraform plan -out tfplan.binary
if %ERRORLEVEL% neq 0 (
    echo ERROR: terraform plan failed.
    pause
    exit /b 1
)

echo === Converting plan to text ===
terraform show -no-color tfplan.binary > tfplan.txt
if %ERRORLEVEL% neq 0 (
    echo ERROR: terraform show failed.
    pause
    exit /b 1
)

echo === Masking sensitive values ===
REM Uses PowerShell for regex substitution — PowerShell is available on all
REM modern Windows systems without any execution policy requirements when
REM called inline like this (no .ps1 file involved).

powershell -Command " ^
    $content = Get-Content tfplan.txt -Raw; ^
    $content = $content -replace '\b\d{12}\b', '<ACCOUNT_ID>'; ^
    $content = $content -replace 'arn:aws:[a-z0-9\-]+:[a-z0-9\-]*:\d+:[a-zA-Z0-9\-_/:.]+', 'arn:aws:<MASKED>'; ^
    $content = $content -replace 'subnet-[0-9a-f]{8,}', '<SUBNET_ID>'; ^
    $content = $content -replace 'sg-[0-9a-f]{8,}', '<SG_ID>'; ^
    $content = $content -replace 'vpc-[0-9a-f]{8,}', '<VPC_ID>'; ^
    $content = $content -replace 'igw-[0-9a-f]{8,}', '<IGW_ID>'; ^
    $content = $content -replace 'rtb-[0-9a-f]{8,}', '<RTB_ID>'; ^
    $content = $content -replace 'rtbassoc-[0-9a-f]{8,}', '<ASSOC_ID>'; ^
    $content = $content -replace 'nat-[0-9a-f]{8,}', '<NAT_ID>'; ^
    $content = $content -replace '[a-z0-9\-]+\.[a-z0-9]+\.[0-9a-z\-]+\.rds\.amazonaws\.com', '<RDS_ENDPOINT>'; ^
    $content = $content -replace '[a-z0-9\-]+\.[a-z0-9]+\.[0-9]+\.[a-z0-9]+\.cache\.amazonaws\.com', '<REDIS_ENDPOINT>'; ^
    $content = $content -replace '[a-z0-9\-]+-[0-9]+\.[a-z0-9\-]+\.elb\.amazonaws\.com', '<ALB_ENDPOINT>'; ^
    $content = $content -replace '\d{12}\.dkr\.ecr\.[a-z0-9\-]+\.amazonaws\.com/([a-z0-9\-]+):[a-zA-Z0-9\-_.:]+', '<ECR_REGISTRY>/$1:<IMAGE_TAG>'; ^
    $content = $content -replace '\"\/trip-me-buddy\/[a-z0-9\-]+\"', '\"/trip-me-buddy/<PARAM_NAME>\"'; ^
    $content = $content -replace 'jdbc:postgresql://[^\s\"]+', 'jdbc:postgresql://<RDS_ENDPOINT>/<DB_NAME>'; ^
    $content = $content -replace '\b[0-9a-f]{40}\b', '<GIT_SHA>'; ^
    $content = $content -replace '\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP_ADDRESS>'; ^
    Set-Content tfplan_masked.txt $content -Encoding UTF8; ^
    Write-Host ''; ^
    Write-Host '=== CHANGE SUMMARY ==='; ^
    Get-Content tfplan_masked.txt | Where-Object { ^
        $_ -match '^\s*[+~\-]' -or ^
        $_ -match 'must be replaced' -or ^
        $_ -match 'will be (created^|updated^|destroyed^|replaced)' -or ^
        $_ -match '^Plan:' -or ^
        $_ -match 'No changes' ^
    } ^
"

echo.
echo === Done. Masked plan saved to tfplan_masked.txt ===
echo     Review the CHANGE SUMMARY above, then share tfplan_masked.txt if needed.
pause
