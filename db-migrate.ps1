# ============================================================================
# TripMeBuddy - Database Migration Script
# Automated SQL migration execution via Bastion host
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$MigrationFile,
    
    [switch]$Verify,
    [switch]$SkipVerify,
    [switch]$Force
)

# Import utilities
. "$PSScriptRoot\utils.ps1"

# ============================================================================
# MAIN MIGRATION FUNCTION
# ============================================================================

function Run-Migration {
    Show-ScriptHeader `
        -Title "TripMeBuddy - Database Migration" `
        -Description "Automated SQL migration via Bastion host"
    
    # Load environment
    if (-not (Load-Environment)) {
        Write-Error-Custom "Failed to load environment. Exiting."
        return $false
    }
    
    # Validate migration file
    Write-Step "Validating migration file..."
    
    $migrationPath = if (Test-Path $MigrationFile) {
        Resolve-Path $MigrationFile
    }
    elseif (Test-Path (Join-Path $MIGRATIONS_PATH $MigrationFile)) {
        Resolve-Path (Join-Path $MIGRATIONS_PATH $MigrationFile)
    }
    else {
        Write-Error-Custom "Migration file not found: $MigrationFile"
        Write-Info "Searched in:"
        Write-Info "  - $MigrationFile"
        Write-Info "  - $MIGRATIONS_PATH\$MigrationFile"
        return $false
    }
    
    Write-Success "Migration file: $migrationPath"
    
    # Display migration preview
    Write-Step "Migration Preview"
    Write-Info "First 20 lines of migration:"
    Write-Separator
    Get-Content $migrationPath -TotalCount 20 | ForEach-Object {
        Write-Host $_ -ForegroundColor Gray
    }
    Write-Separator
    
    # Confirm migration
    if (-not $Force) {
        if (-not (Confirm-Action "Execute this migration?")) {
            Write-Warning-Custom "Migration cancelled by user"
            return $false
        }
    }
    
    # ========================================================================
    # BASTION HOST SETUP
    # ========================================================================
    
    # Get Bastion instance
    $bastionId = Get-BastionInstanceId
    if (-not $bastionId) {
        return $false
    }
    
    # Start Bastion
    $bastionInfo = Start-BastionHost -InstanceId $bastionId
    if (-not $bastionInfo) {
        return $false
    }
    
    $script:shouldStopBastion = $bastionInfo.WasStarted
    
    # Get Bastion IP
    $bastionIp = Get-BastionPublicIp -InstanceId $bastionId
    if (-not $bastionIp) {
        Cleanup-Bastion -InstanceId $bastionId
        return $false
    }
    
    # Get DB endpoint
    $dbEndpoint = Get-DBEndpoint
    if (-not $dbEndpoint) {
        Cleanup-Bastion -InstanceId $bastionId
        return $false
    }
    
    # ========================================================================
    # COPY MIGRATION TO BASTION
    # ========================================================================
    
    Write-Step "Copying migration file to Bastion..."
    
    $remotePath = "/home/$SSH_USER/$(Split-Path $migrationPath -Leaf)"
    
    $scpCommand = "scp -i `"$SSH_KEY_PATH`" -o StrictHostKeyChecking=no `"$migrationPath`" ${SSH_USER}@${bastionIp}:$remotePath"
    Write-Info "Command: $scpCommand"
    
    Invoke-Expression $scpCommand
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to copy migration file to Bastion"
        Cleanup-Bastion -InstanceId $bastionId
        return $false
    }
    
    Write-Success "Migration file copied to Bastion: $remotePath"
    
    # ========================================================================
    # VERIFY PGPASS FILE
    # ========================================================================
    
    Write-Step "Verifying database credentials..."
    
    $pgpassCheck = "ssh -i `"$SSH_KEY_PATH`" -o StrictHostKeyChecking=no ${SSH_USER}@${bastionIp} 'test -f ~/.pgpass && echo EXISTS || echo MISSING'"
    $pgpassExists = Invoke-Expression $pgpassCheck
    
    if ($pgpassExists -notmatch "EXISTS") {
        Write-Warning-Custom "~/.pgpass file not found on Bastion"
        Write-Info "Creating .pgpass file..."
        
        # Create .pgpass content
        $pgpassContent = "${dbEndpoint}:${DB_PORT}:${DB_NAME}:${DB_USERNAME}:${DB_PASSWORD}"
        
        # Create and set permissions for .pgpass
        $createPgpass = @"
ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no ${SSH_USER}@${bastionIp} "echo '$pgpassContent' > ~/.pgpass && chmod 600 ~/.pgpass"
"@
        
        Invoke-Expression $createPgpass
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to create .pgpass file"
            Cleanup-Bastion -InstanceId $bastionId
            return $false
        }
        
        Write-Success ".pgpass file created successfully"
    }
    else {
        Write-Success ".pgpass file exists"
    }
    
    # ========================================================================
    # EXECUTE MIGRATION
    # ========================================================================
    
    Write-Step "Executing migration..."
    Write-Info "Database: $DB_NAME"
    Write-Info "User: $DB_USERNAME"
    
    $migrationCommand = @"
ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no ${SSH_USER}@${bastionIp} "PGSSLMODE=require psql -h $dbEndpoint -U $DB_USERNAME -d $DB_NAME -f $remotePath"
"@
    
    Write-Info "Command: $migrationCommand"
    
    Invoke-Expression $migrationCommand
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Migration execution failed"
        Write-Warning-Custom "Check the error messages above for details"
        Cleanup-Bastion -InstanceId $bastionId
        return $false
    }
    
    Write-Success "Migration executed successfully"
    
    # ========================================================================
    # VERIFICATION
    # ========================================================================
    
    if ($Verify -or (-not $SkipVerify)) {
        Write-Step "Verifying migration..."
        
        # Try to detect what the migration created by parsing the file
        $migrationContent = Get-Content $migrationPath -Raw
        
        # Check for CREATE TABLE statements
        if ($migrationContent -match "CREATE TABLE\s+(\w+)") {
            $tableName = $matches[1]
            Write-Info "Detected table creation: $tableName"
            
            # Verify table exists
            $verifyTable = @"
ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no ${SSH_USER}@${bastionIp} "PGSSLMODE=require psql -h $dbEndpoint -U $DB_USERNAME -d $DB_NAME -c '\dt $tableName'"
"@
            
            Write-Info "Verifying table: $tableName"
            Invoke-Expression $verifyTable
            
            # Get table structure
            $describeTable = @"
ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no ${SSH_USER}@${bastionIp} "PGSSLMODE=require psql -h $dbEndpoint -U $DB_USERNAME -d $DB_NAME -c '\d $tableName'"
"@
            
            Write-Info "Table structure:"
            Invoke-Expression $describeTable
        }
        
        # List all tables
        Write-Step "Current database tables:"
        $listTables = @"
ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no ${SSH_USER}@${bastionIp} "PGSSLMODE=require psql -h $dbEndpoint -U $DB_USERNAME -d $DB_NAME -c '\dt'"
"@
        
        Invoke-Expression $listTables
        
        Write-Success "Migration verification complete"
    }
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    # Remove migration file from Bastion
    Write-Step "Cleaning up..."
    
    $removeFile = @"
ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no ${SSH_USER}@${bastionIp} "rm -f $remotePath"
"@
    
    Invoke-Expression $removeFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Temporary files removed from Bastion"
    }
    
    Cleanup-Bastion -InstanceId $bastionId
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    Write-Separator
    Write-Success "Migration completed successfully!"
    Write-Separator
    
    Write-Info "Migration file: $(Split-Path $migrationPath -Leaf)"
    Write-Info "Database: $DB_NAME"
    Write-Info "Endpoint: $dbEndpoint"
    Write-Host ""
    
    return $true
}

function Cleanup-Bastion {
    param([string]$InstanceId)
    
    if ($InstanceId -and $script:shouldStopBastion) {
        Stop-BastionHost -InstanceId $InstanceId -WasStartedByScript $script:shouldStopBastion
    }
}

# ============================================================================
# INTERACTIVE MODE
# ============================================================================

function Run-Interactive-Migration {
    Show-ScriptHeader `
        -Title "TripMeBuddy - Database Migration (Interactive)" `
        -Description "Select and execute a migration file"
    
    # Load environment
    if (-not (Load-Environment)) {
        Write-Error-Custom "Failed to load environment. Exiting."
        return
    }
    
    # List available migrations
    Write-Step "Available migration files:"
    
    if (-not (Test-Path $MIGRATIONS_PATH)) {
        Write-Error-Custom "Migrations directory not found: $MIGRATIONS_PATH"
        return
    }
    
    $migrations = Get-ChildItem -Path $MIGRATIONS_PATH -Filter "*.sql" | Sort-Object Name
    
    if ($migrations.Count -eq 0) {
        Write-Warning-Custom "No migration files found in $MIGRATIONS_PATH"
        return
    }
    
    for ($i = 0; $i -lt $migrations.Count; $i++) {
        Write-Host "  [$($i + 1)] " -ForegroundColor Cyan -NoNewline
        Write-Host $migrations[$i].Name
    }
    
    Write-Host ""
    Write-Host "Select migration number (or 'q' to quit): " -ForegroundColor Magenta -NoNewline
    $selection = Read-Host
    
    if ($selection -eq 'q') {
        Write-Info "Cancelled by user"
        return
    }
    
    try {
        $index = [int]$selection - 1
        if ($index -lt 0 -or $index -ge $migrations.Count) {
            Write-Error-Custom "Invalid selection"
            return
        }
        
        $selectedMigration = $migrations[$index].FullName
        
        # Run migration
        $script:MigrationFile = $selectedMigration
        Run-Migration
    }
    catch {
        Write-Error-Custom "Invalid input"
    }
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

try {
    if (-not $MigrationFile) {
        # Interactive mode
        Run-Interactive-Migration
    }
    else {
        # Direct execution mode
        $success = Run-Migration
        
        if ($success) {
            exit 0
        }
        else {
            Write-Error-Custom "Migration failed"
            exit 1
        }
    }
}
catch {
    Write-Error-Custom "Unexpected error: $_"
    Write-Error-Custom $_.ScriptStackTrace
    
    if ($bastionId) {
        Cleanup-Bastion -InstanceId $bastionId
    }
    
    exit 1
}
