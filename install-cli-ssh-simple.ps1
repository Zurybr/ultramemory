# Ultramemory CLI SSH Installer for Windows (Non-Interactive)
param(
    [string]$ServerIP = "192.168.100.18",
    [string]$SSHUser = "zurybr",
    [string]$SSHPassword = "brandom391"
)

$ErrorActionPreference = "Stop"

Write-Host "Installing Ultramemory CLI via SSH..." -ForegroundColor Cyan
Write-Host "Server: $SSHUser@$ServerIP" -ForegroundColor Yellow

# Test SSH connection first
Write-Host "Testing SSH connection..."
$test = ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSHUser@$ServerIP" "echo OK" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Trying with password..."
    # Use sshpass if available
    $sshpass = Get-Command sshpass -ErrorAction SilentlyContinue
    if ($sshpass) {
        $test = sshpass -p $SSHPassword ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSHUser@$ServerIP" "echo OK" 2>&1
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Cannot connect to server" -ForegroundColor Red
        exit 1
    }
}

Write-Host "SSH connection OK!" -ForegroundColor Green

# Create config directory
$configDir = "$env:USERPROFILE\.ulmemory"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

# Save SSH config
$sshConfig = @{
    server_ip = $ServerIP
    ssh_user = $SSHUser
    use_sshpass = $false
    created_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
}

# Check for sshpass
$sshpassCmd = Get-Command sshpass -ErrorAction SilentlyContinue
if ($sshpassCmd -and $SSHPassword) {
    $sshConfig.use_sshpass = $true
    $sshConfig.sshpass_path = $sshpassCmd.Source
    $sshConfig.encrypted_password = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($SSHPassword))
}

$sshConfig | ConvertTo-Json | Set-Content "$configDir\ssh_config.json" -Encoding UTF8
Write-Host "Config saved!" -ForegroundColor Green

# Create wrapper function
$wrapper = @"
function ulmemory {
    `$configDir = "`$env:USERPROFILE\.ulmemory"
    `$sshConfig = Get-Content "`$configDir\ssh_config.json" | ConvertFrom-Json
    `$serverIP = `$sshConfig.server_ip
    `$sshUser = `$sshConfig.ssh_user

    `$cmd = "ulmemory " + (`$Args -join " ")

    if (`$sshConfig.use_sshpass) {
        `$pass = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(`$sshConfig.encrypted_password))
        `$sshpass = `$sshConfig.sshpass_path
        & `$sshpass -p `$pass ssh -o StrictHostKeyChecking=no "`$sshUser@`$serverIP" `$cmd
    } else {
        ssh -o StrictHostKeyChecking=no "`$sshUser@`$serverIP" `$cmd
    }
}
"@

Set-Content "$configDir\ulmemory_ssh.ps1" -Value $wrapper -Encoding UTF8

# Add to profile
$profileEntry = @"

. "$configDir\ulmemory_ssh.ps1"
"@

$profilePath = $PROFILE
if (Test-Path $profilePath) {
    $content = Get-Content $profilePath -Raw
    if ($content -notmatch "ulmemory_ssh\.ps1") {
        Add-Content $profilePath $profileEntry
    }
} else {
    Set-Content $profilePath $profileEntry
}

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "Restart PowerShell and use: ulmemory add `"test`""
