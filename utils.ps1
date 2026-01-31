# ============================================================================
# TripMeBuddy - PowerShell Utilities
# Common functions for deployment and migration scripts
# ============================================================================

# Color codes for output
$script:Colors = @{
    Success = "Green"
    Error = "Red"
    Warning = "Yellow"
    Info = "Cyan"
    Prompt = "Magenta"
}

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor $Colors.Success
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Error
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Warning
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Info
}

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor $Colors.Info
}

function Write-Separator {
    Write-Host ("=" * 80) -ForegroundColor Gray
}

# ============================================================================
# ENVIRONMENT LOADING
# ============================================================================

function Load-Environment {
    param([string]$EnvFilePath = ".env.local")

    Write-Step "Loading environment configuration..."

    if (-not (Test-Path $EnvFilePath)) {
        Write-Error-Custom "Environment file not found: $EnvFilePath"
        Write-Warning-Custom "Please copy .env.local.template to .env.local and configure it"
        return $false
    }

    Get-Content $EnvFilePath | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.+)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()

            # Expand variables in value
            $value = $ExecutionContext.InvokeCommand.ExpandString($value)

            Set-Variable -Name $name -Value $value -Scope Global
            [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
        }
    }

    Write-Success "Environment loaded from $EnvFilePath"
    return $true
}

# ============================================================================
# AWS RESOURCE FUNCTIONS
# ============================================================================

function Get-ECRRepositoryUrl {
    Write-Step "Getting ECR repository URL..."

    try {
        $url = aws ecr describe-repositories `
            --repository-names $ECR_REPOSITORY_NAME `
            --query 'repositories[0].repositoryUri' `
            --output text `
            --region $AWS_REGION 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to get ECR repository URL"
            Write-Error-Custom $url
            return $null
        }

        Write-Success "ECR URL: $url"
        return $url
    }
    catch {
        Write-Error-Custom "Error getting ECR repository URL: $_"
        return $null
    }
}

function Get-BastionInstanceId {
    Write-Step "Getting Bastion instance ID..."

    try {
        $instanceId = aws ec2 describe-instances `
            --region $AWS_REGION `
            --filters "Name=tag:Name,Values=$BASTION_TAG_NAME" "Name=instance-state-name,Values=stopped,running" `
            --query "Reservations[0].Instances[0].InstanceId" `
            --output text 2>&1

        if ($LASTEXITCODE -ne 0 -or $instanceId -eq "None") {
            Write-Error-Custom "Failed to get Bastion instance ID"
            return $null
        }

        Write-Success "Bastion ID: $instanceId"
        return $instanceId
    }
    catch {
        Write-Error-Custom "Error getting Bastion instance ID: $_"
        return $null
    }
}

function Get-BastionInstanceState {
    param([string]$InstanceId)

    try {
        $state = aws ec2 describe-instances `
            --instance-ids $InstanceId `
            --region $AWS_REGION `
            --query "Reservations[0].Instances[0].State.Name" `
            --output text 2>&1

        if ($LASTEXITCODE -ne 0) {
            return $null
        }

        return $state
    }
    catch {
        return $null
    }
}

function Start-BastionHost {
    param([string]$InstanceId)

    $currentState = Get-BastionInstanceState -InstanceId $InstanceId

    if ($currentState -eq "running") {
        Write-Info "Bastion host is already running"
        return @{ WasStarted = $false; State = "running" }
    }

    Write-Step "Starting Bastion host..."

    try {
        aws ec2 start-instances --instance-ids $InstanceId --region $AWS_REGION | Out-Null

        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to start Bastion host"
            return $null
        }

        Write-Info "Waiting for Bastion to reach running state..."
        aws ec2 wait instance-running --instance-ids $InstanceId --region $AWS_REGION

        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Timeout waiting for Bastion to start"
            return $null
        }

        Write-Info "Waiting for SSH to be ready..."
        Start-Sleep -Seconds 10

        Write-Success "Bastion host started successfully"
        return @{ WasStarted = $true; State = "running" }
    }
    catch {
        Write-Error-Custom "Error starting Bastion host: $_"
        return $null
    }
}

function Stop-BastionHost {
    param(
        [string]$InstanceId,
        [bool]$WasStartedByScript = $false
    )

    if (-not $WasStartedByScript -and -not $AUTO_STOP_BASTION) {
        Write-Info "Bastion was already running and AUTO_STOP_BASTION is false"
        Write-Warning-Custom "Remember to manually stop the Bastion host to save costs!"
        return
    }

    Write-Step "Stopping Bastion host to save costs..."

    try {
        aws ec2 stop-instances --instance-ids $InstanceId --region $AWS_REGION | Out-Null

        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to stop Bastion host"
            return $false
        }

        Write-Success "Bastion host stopped successfully"
        return $true
    }
    catch {
        Write-Error-Custom "Error stopping Bastion host: $_"
        return $false
    }
}

function Get-BastionPublicIp {
    param([string]$InstanceId)

    Write-Step "Getting Bastion public IP..."

    try {
        $ip = aws ec2 describe-instances `
            --instance-ids $InstanceId `
            --region $AWS_REGION `
            --query "Reservations[0].Instances[0].PublicIpAddress" `
            --output text 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to get Bastion public IP"
            return $null
        }

        Write-Success "Bastion IP: $ip"
        return $ip
    }
    catch {
        Write-Error-Custom "Error getting Bastion public IP: $_"
        return $null
    }
}

function Get-DBEndpoint {
    Write-Step "Getting RDS database endpoint..."

    try {
        $endpoint = aws rds describe-db-instances `
            --db-instance-identifier $DB_INSTANCE_IDENTIFIER `
            --region $AWS_REGION `
            --query "DBInstances[0].Endpoint.Address" `
            --output text 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to get DB endpoint"
            return $null
        }

        Write-Success "DB Endpoint: $endpoint"
        return $endpoint
    }
    catch {
        Write-Error-Custom "Error getting DB endpoint: $_"
        return $null
    }
}

# ============================================================================
# USER INTERACTION FUNCTIONS
# ============================================================================

function Confirm-Action {
    param(
        [string]$Message,
        [bool]$DefaultYes = $true
    )

    $prompt = if ($DefaultYes) { "$Message (Y/n)" } else { "$Message (y/N)" }
    Write-Host $prompt -ForegroundColor $Colors.Prompt -NoNewline
    Write-Host " " -NoNewline

    $response = Read-Host

    if ([string]::IsNullOrWhiteSpace($response)) {
        return $DefaultYes
    }

    return $response -match '^[Yy]'
}

function Wait-ForKeyPress {
    param([string]$Message = "Press any key to continue...")

    Write-Host "`n$Message" -ForegroundColor $Colors.Prompt
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
}

# ============================================================================
# ERROR HANDLING
# ============================================================================

function Test-CommandExists {
    param([string]$Command)

    $exists = $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)

    if (-not $exists) {
        Write-Error-Custom "Required command not found: $Command"
        Write-Warning-Custom "Please install $Command and ensure it is in your PATH"
    }

    return $exists
}

function Test-Prerequisites {
    Write-Step "Checking prerequisites..."

    $required = @("aws", "docker")
    $allExist = $true

    foreach ($cmd in $required) {
        if (-not (Test-CommandExists $cmd)) {
            $allExist = $false
        }
    }

    if ($allExist) {
        Write-Success "All prerequisites satisfied"
    }

    return $allExist
}

# ============================================================================
# SCRIPT HEADER
# ============================================================================

function Show-ScriptHeader {
    param(
        [string]$Title,
        [string]$Description
    )

    Clear-Host
    Write-Separator
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "  $Description" -ForegroundColor Gray
    Write-Separator
}

# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

Export-ModuleMember -Function *