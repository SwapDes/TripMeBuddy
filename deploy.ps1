# ============================================================================
# TripMeBuddy - Automated ECS Deployment Script
# Builds Docker image and deploys to AWS ECS with error handling
# ============================================================================

param(
    [switch]$NoCache,
    [switch]$SkipBuild,
    [switch]$SkipDeploy,
    [switch]$StopBastion,
    [switch]$Force
)

# Import utilities
. "$PSScriptRoot\utils.ps1"

# ============================================================================
# MAIN DEPLOYMENT FUNCTION
# ============================================================================

function Deploy-Backend {
    Show-ScriptHeader `
        -Title "TripMeBuddy - Backend Deployment" `
        -Description "Automated Docker build and ECS deployment"
    
    # Load environment
    if (-not (Load-Environment)) {
        Write-Error-Custom "Failed to load environment. Exiting."
        return $false
    }
    
    # Check prerequisites
    if (-not (Test-Prerequisites)) {
        return $false
    }
    
    # Display configuration
    Write-Step "Deployment Configuration"
    Write-Info "Region: $AWS_REGION"
    Write-Info "ECS Cluster: $ECS_CLUSTER_NAME"
    Write-Info "ECS Service: $ECS_SERVICE_NAME"
    Write-Info "ECR Repository: $ECR_REPOSITORY_NAME"
    Write-Info "Backend Path: $BACKEND_PATH"
    Write-Host ""
    
    # Confirm deployment
    if (-not $Force) {
        if (-not (Confirm-Action "Proceed with deployment?")) {
            Write-Warning-Custom "Deployment cancelled by user"
            return $false
        }
    }
    
    # Get Bastion state (for cleanup at end)
    Write-Step "Checking Bastion host status..."
    $bastionId = Get-BastionInstanceId
    if ($bastionId) {
        $bastionInfo = Start-BastionHost -InstanceId $bastionId
        $script:shouldStopBastion = $bastionInfo.WasStarted -or $StopBastion
    }
    
    # Navigate to backend directory
    Write-Step "Navigating to backend directory..."
    if (-not (Test-Path $BACKEND_PATH)) {
        Write-Error-Custom "Backend path not found: $BACKEND_PATH"
        return $false
    }
    
    Set-Location $BACKEND_PATH
    Write-Success "Working directory: $(Get-Location)"
    
    # ========================================================================
    # DOCKER BUILD
    # ========================================================================
    
    if (-not $SkipBuild) {
        $useNoCache = $NoCache -or ($FORCE_NO_CACHE -eq "true")
        $cacheFlag = if ($useNoCache) { "--no-cache" } else { "" }
        
        Write-Step "Building Docker image..."
        if ($useNoCache) {
            Write-Warning-Custom "Building with --no-cache (fresh build)"
        }
        
        $buildCommand = "docker build $cacheFlag -t trip-me-buddy-backend ."
        Write-Info "Command: $buildCommand"
        
        Invoke-Expression $buildCommand
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Docker build failed"
            Cleanup-Bastion
            return $false
        }
        
        Write-Success "Docker image built successfully"
    }
    else {
        Write-Warning-Custom "Skipping Docker build (using existing image)"
    }
    
    # ========================================================================
    # ECR PUSH
    # ========================================================================
    
    if (-not $SkipDeploy) {
        # Get ECR URL
        $ecrUrl = Get-ECRRepositoryUrl
        if (-not $ecrUrl) {
            Write-Error-Custom "Failed to get ECR repository URL"
            Cleanup-Bastion
            return $false
        }
        
        # Authenticate to ECR
        Write-Step "Authenticating Docker to ECR..."
        
        $password = aws ecr get-login-password --region $AWS_REGION
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to get ECR login password"
            Cleanup-Bastion
            return $false
        }
        
        $password | docker login --username AWS --password-stdin $ecrUrl
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Docker login to ECR failed"
            Cleanup-Bastion
            return $false
        }
        
        Write-Success "Authenticated to ECR"
        
        # Tag image
        Write-Step "Tagging Docker image..."
        docker tag trip-me-buddy-backend:latest "${ecrUrl}:latest"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to tag Docker image"
            Cleanup-Bastion
            return $false
        }
        
        Write-Success "Image tagged: ${ecrUrl}:latest"
        
        # Push to ECR
        Write-Step "Pushing image to ECR..."
        Write-Info "This may take a few minutes..."
        
        docker push "${ecrUrl}:latest"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to push image to ECR"
            Cleanup-Bastion
            return $false
        }
        
        Write-Success "Image pushed to ECR successfully"
        
        # ====================================================================
        # ECS DEPLOYMENT
        # ====================================================================
        
        Write-Step "Updating ECS service..."
        Write-Info "Forcing new deployment with latest image"
        
        aws ecs update-service `
            --cluster $ECS_CLUSTER_NAME `
            --service $ECS_SERVICE_NAME `
            --force-new-deployment `
            --region $AWS_REGION | Out-Null
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to update ECS service"
            Cleanup-Bastion
            return $false
        }
        
        Write-Success "ECS service update initiated"
        
        # Wait for deployment
        Write-Step "Waiting for ECS deployment to stabilize..."
        Write-Info "This typically takes 3-5 minutes"
        Write-Info "Timeout: $ECS_DEPLOYMENT_TIMEOUT seconds"
        
        $waitStartTime = Get-Date
        
        # Use Start-Job to run with timeout
        $job = Start-Job -ScriptBlock {
            param($cluster, $service, $region)
            aws ecs wait services-stable `
                --cluster $cluster `
                --services $service `
                --region $region
            return $LASTEXITCODE
        } -ArgumentList $ECS_CLUSTER_NAME, $ECS_SERVICE_NAME, $AWS_REGION
        
        $completed = Wait-Job -Job $job -Timeout $ECS_DEPLOYMENT_TIMEOUT
        
        if ($completed) {
            $exitCode = Receive-Job -Job $job
            Remove-Job -Job $job
            
            if ($exitCode -eq 0) {
                $duration = ((Get-Date) - $waitStartTime).TotalSeconds
                Write-Success "ECS deployment completed successfully in $([math]::Round($duration, 1)) seconds"
            }
            else {
                Write-Error-Custom "ECS deployment failed"
                Cleanup-Bastion
                return $false
            }
        }
        else {
            Remove-Job -Job $job -Force
            Write-Warning-Custom "Deployment timeout exceeded"
            Write-Info "Deployment is still in progress. Check AWS Console for status."
        }
        
        # ====================================================================
        # VERIFY DEPLOYMENT
        # ====================================================================
        
        Write-Step "Verifying deployment..."
        
        $taskCount = aws ecs describe-services `
            --cluster $ECS_CLUSTER_NAME `
            --services $ECS_SERVICE_NAME `
            --region $AWS_REGION `
            --query "services[0].runningCount" `
            --output text
        
        if ($taskCount -gt 0) {
            Write-Success "Service is running with $taskCount task(s)"
        }
        else {
            Write-Warning-Custom "No tasks currently running"
        }
        
        # Get task definition
        $taskDefArn = aws ecs describe-services `
            --cluster $ECS_CLUSTER_NAME `
            --services $ECS_SERVICE_NAME `
            --region $AWS_REGION `
            --query "services[0].taskDefinition" `
            --output text
        
        if ($taskDefArn) {
            $taskDefName = $taskDefArn.Split('/')[-1]
            Write-Info "Task Definition: $taskDefName"
        }
        
        Write-Success "Deployment verification complete"
    }
    else {
        Write-Warning-Custom "Skipping ECR push and ECS deployment"
    }
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    Cleanup-Bastion
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    Write-Separator
    Write-Success "Deployment completed successfully!"
    Write-Separator
    
    Write-Info "Next steps:"
    Write-Info "  1. Check CloudWatch logs for any errors"
    Write-Info "  2. Test endpoints via ALB DNS"
    Write-Info "  3. Verify health check: http://<ALB-DNS>/health"
    Write-Host ""
    
    # Get ALB DNS
    $albDns = aws elbv2 describe-load-balancers `
        --region $AWS_REGION `
        --query "LoadBalancers[?contains(LoadBalancerName, 'trip-me-buddy')].DNSName" `
        --output text 2>$null
    
    if ($albDns) {
        Write-Info "ALB DNS: http://$albDns"
        Write-Info "Health Check: http://$albDns/health"
        Write-Info "API Docs: http://$albDns/docs"
    }
    
    Write-Host ""
    
    return $true
}

function Cleanup-Bastion {
    if ($bastionId -and $script:shouldStopBastion) {
        Stop-BastionHost -InstanceId $bastionId -WasStartedByScript $script:shouldStopBastion
    }
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

try {
    $success = Deploy-Backend
    
    if ($success) {
        exit 0
    }
    else {
        Write-Error-Custom "Deployment failed"
        exit 1
    }
}
catch {
    Write-Error-Custom "Unexpected error: $_"
    Write-Error-Custom $_.ScriptStackTrace
    Cleanup-Bastion
    exit 1
}
finally {
    # Return to original directory
    Set-Location $PSScriptRoot
}
