# Ultramemory CLI SSH Installer for Windows PowerShell
# Run with: powershell -ExecutionPolicy Bypass -File install-cli-ssh.ps1
param(
    [string]$ServerIP = "",      # IP del servidor remoto
    [string]$SSHUser = "",       # Usuario SSH
    [string]$SSHPassword = "",   # Contraseña SSH (opcional si usa clave)
    [bool]$UploadSSHKey = $false # Subir clave SSH automaticamente
)

$ErrorActionPreference = "Stop"

# Banner
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Ultramemory CLI SSH Installer for Windows    ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ============================================
# Step 1: Gather SSH Configuration
# ============================================

Write-Host "[1/4] Configuring SSH Connection..." -ForegroundColor Yellow

# Get Server IP
if (-not $ServerIP) {
    Write-Host "Enter the server IP address:" -ForegroundColor White
    $ServerIP = Read-Host "  (e.g., 192.168.1.100 or server.example.com)"
}

if (-not $ServerIP) {
    Write-Host "Error: Server IP is required" -ForegroundColor Red
    exit 1
}

# Get SSH User
if (-not $SSHUser) {
    Write-Host "Enter the SSH username:" -ForegroundColor White
    $SSHUser = Read-Host "  (e.g., zurybr)"
}

if (-not $SSHUser) {
    Write-Host "Error: SSH username is required" -ForegroundColor Red
    exit 1
}

# Check if SSH key exists
$sshKeyPath = "$env:USERPROFILE\.ssh\id_rsa"
$hasSSHKey = Test-Path $sshKeyPath

Write-Host ""
Write-Host "SSH Key Status: " -NoNewline
if ($hasSSHKey) {
    Write-Host "Found at $sshKeyPath" -ForegroundColor Green
} else {
    Write-Host "Not found" -ForegroundColor Yellow
}

# If no SSH key, ask if user wants to generate and upload
if (-not $hasSSHKey) {
    Write-Host ""
    $keyChoice = Read-Host "No SSH key found. Generate and upload to server? (y/n)"
    if ($keyChoice -eq "y" -or $keyChoice -eq "Y") {
        $UploadSSHKey = $true
    }
}

# Handle SSH key generation and upload
if ($UploadSSHKey -and -not $hasSSHKey) {
    Write-Host ""
    Write-Host "Generating SSH key pair..." -ForegroundColor Cyan

    # Generate SSH key
    $generateKey = Read-Host "Enter a passphrase for the key (or press Enter for no passphrase)"
    if ([string]::IsNullOrEmpty($generateKey)) {
        ssh-keygen -t rsa -b 4096 -f $sshKeyPath -N ""
    } else {
        ssh-keygen -t rsa -b 4096 -f $sshKeyPath -N $generateKey
    }

    Write-Host "SSH key generated successfully!" -ForegroundColor Green
    $hasSSHKey = $true
}

# Upload SSH key if requested and we have a password
if ($UploadSSHKey -and $hasSSHKey) {
    Write-Host ""
    Write-Host "Uploading SSH key to server..." -ForegroundColor Cyan

    # Get password if not provided
    if (-not $SSHPassword) {
        Write-Host "Enter password for $SSHUser@$ServerIP:" -ForegroundColor White
        $SSHPassword = Read-Host -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SSHPassword)
        $SSHPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    }

    # Use sshpass if available, otherwise manual method
    $sshpassCmd = Get-Command sshpass -ErrorAction SilentlyContinue

    if ($sshpassCmd) {
        # Use sshpass
        $pubKey = Get-Content "$sshKeyPath.pub"
        echo $pubKey | sshpass ssh -o StrictHostKeyChecking=no "$SSHUser@$ServerIP" "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
    } else {
        Write-Host "sshpass not found. Please manually add this key to the server:" -ForegroundColor Yellow
        Write-Host ""
        Get-Content "$sshKeyPath.pub"
        Write-Host ""
        Write-Host "Add the above key to ~/.ssh/authorized_keys on the server" -ForegroundColor Yellow
        Write-Host "Press Enter when done..."
        Read-Host
    }

    Write-Host "SSH key uploaded successfully!" -ForegroundColor Green
}

# Test SSH connection
Write-Host ""
Write-Host "Testing SSH connection to $SSHUser@$ServerIP..." -ForegroundColor Cyan
$testResult = ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSHUser@$ServerIP" "echo 'SSH connection OK'" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Could not connect without password. Testing with password..." -ForegroundColor Yellow

    if (-not $SSHPassword) {
        Write-Host "Enter password for $SSHUser@$ServerIP:" -ForegroundColor White
        $SSHPassword = Read-Host -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SSHPassword)
        $SSHPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    }

    # Try with sshpass if available
    $sshpassCmd = Get-Command sshpass -ErrorAction SilentlyContinue
    if ($sshpassCmd) {
        $testResult = sshpass -p $SSHPassword ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSHUser@$ServerIP" "echo 'SSH connection OK'" 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error: Could not establish SSH connection" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Error: Cannot test connection without password or sshpass. Please configure SSH key authentication." -ForegroundColor Red
        exit 1
    }
}

Write-Host "SSH connection verified!" -ForegroundColor Green

# ============================================
# Step 2: Test if Ultramemory exists on server
# ============================================

Write-Host ""
Write-Host "[2/4] Verifying Ultramemory installation on server..." -ForegroundColor Yellow

$remoteCheck = ssh -o ConnectTimeout=10 "$SSHUser@$ServerIP" "which ulmemory" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Ultramemory CLI not found on server" -ForegroundColor Red
    Write-Host "Please install Ultramemory on the server first using install-cli.sh" -ForegroundColor Yellow
    exit 1
}

Write-Host "Ultramemory found on server!" -ForegroundColor Green

# ============================================
# Step 3: Create local configuration
# ============================================

Write-Host ""
Write-Host "[3/4] Creating local SSH configuration..." -ForegroundColor Yellow

# Create config directory
$configDir = "$env:USERPROFILE\.ulmemory"
$agentsDir = "$configDir\agents"
$logsDir = "$configDir\logs"

if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}
if (-not (Test-Path $agentsDir)) {
    New-Item -ItemType Directory -Path $agentsDir -Force | Out-Null
}
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

# Create SSH config file
$sshConfigFile = "$configDir\ssh_config.json"

$sshConfig = @{
    server_ip = $ServerIP
    ssh_user = $SSHUser
    use_sshpass = $false
    sshpass_path = ""
    created_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
}

# Check if sshpass is available for password-based connections
$sshpassCmd = Get-Command sshpass -ErrorAction SilentlyContinue
if ($sshpassCmd -and $SSHPassword) {
    $sshConfig.use_sshpass = $true
    $sshConfig.sshpass_path = $sshpassCmd.Source

    # Save encrypted password (simple base64 for now - in production use more secure method)
    $sshConfig.encrypted_password = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($SSHPassword))
}

$sshConfig | ConvertTo-Json -Depth 10 | Set-Content -Path $sshConfigFile -Encoding UTF8
Write-Host "SSH config saved to $sshConfigFile" -ForegroundColor Green

# ============================================
# Step 4: Create SSH wrapper script
# ============================================

Write-Host ""
Write-Host "[4/4] Creating SSH wrapper script..." -ForegroundColor Yellow

$scriptsDir = "$env:USERPROFILE\AppData\Local\Programs\ulmemory"
if (-not (Test-Path $scriptsDir)) {
    New-Item -ItemType Directory -Path $scriptsDir -Force | Out-Null
}

# Create PowerShell wrapper function
$wrapperFunction = @"
# Ultramemory CLI SSH Wrapper
# This wrapper executes commands on the remote server via SSH
`$ErrorActionPreference = "Stop"

# Load SSH config
`$configDir = "`$env:USERPROFILE\.ulmemory"
`$sshConfigFile = "`$configDir\ssh_config.json"

if (-not (Test-Path `$sshConfigFile)) {
    Write-Host "Error: SSH config not found. Run install-cli-ssh.ps1 first." -ForegroundColor Red
    exit 1
}

`$sshConfig = Get-Content `$sshConfigFile | ConvertFrom-Json

`$serverIP = `$sshConfig.server_ip
`$sshUser = `$sshConfig.ssh_user
`$useSshpass = `$sshConfig.use_sshpass
`$sshpassPath = `$sshConfig.sshpass_path
`$encryptedPassword = `$sshConfig.encrypted_password

function Invoke-UlmemorySSH {
    param(
        [Parameter(ValueFromRemainingArguments=`$true)]
        [string[]]`$Args
    )

    `$remoteCmd = "ulmemory " + (`$Args -join " ")

    if (`$useSshpass -and `$encryptedPassword) {
        `$password = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(`$encryptedPassword))

        if (Test-Path `$sshpassPath) {
            `$result = & `$sshpassPath -p `$password ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "`$sshUser@`$serverIP" `$remoteCmd 2>&1
        } else {
            Write-Host "Error: sshpass not found at `$sshpassPath" -ForegroundColor Red
            exit 1
        }
    } else {
        `$result = ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "`$sshUser@`$serverIP" `$remoteCmd 2>&1
    }

    if (`$LASTEXITCODE -ne 0) {
        Write-Host `$result -ForegroundColor Red
        exit `$LASTEXITCODE
    }

    Write-Host `$result
}

# Main ulmemory function
function ulmemory {
    # Parse arguments to handle special cases
    `$argString = `$Args -join " "

    # If just --help or -h, show local help
    if (`$argString -match '^\s*(--help|-h)\s*$') {
        Write-Host "Ultramemory CLI (SSH Mode)" -ForegroundColor Cyan
        Write-Host "Commands are executed remotely on `$sshUser@`$serverIP" -ForegroundColor Gray
        Write-Host ""
        Write-Host "To run commands:" -ForegroundColor Yellow
        Write-Host "  ulmemory --help           Show remote help"
        Write-Host "  ulmemory add `"text`"      Add memory"
        Write-Host "  ulmemory query `"term`"    Query memory"
        Write-Host "  ulmemory status           Show status"
        Write-Host "  ulmemory up               Start services on server"
        Write-Host ""
        return
    }

    # Execute remote command
    Invoke-UlmemorySSH @Args
}

# Also create a direct alias to the remote command
Set-Alias -Name ulmemory -Value function:ulmemory -Scope Global -ErrorAction SilentlyContinue
"@

$wrapperFile = "$configDir\ulmemory_ssh_wrapper.ps1"
$wrapperFunction | Set-Content -Path $wrapperFile -Encoding UTF8

# Add to PowerShell profile
$profilePath = $PROFILE
$profileDir = Split-Path -Parent $profilePath

if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}

$profileEntry = @"

# Ultramemory CLI SSH Wrapper
. "$configDir\ulmemory_ssh_wrapper.ps1"
"@

if (-not (Test-Path $profilePath)) {
    $profileEntry | Set-Content -Path $profilePath -Encoding UTF8
} else {
    $existingContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
    if ($existingContent -notmatch "ulmemory_ssh_wrapper\.ps1") {
        Add-Content -Path $profilePath -Value $profileEntry
    }
}

# Create a simple .cmd for direct calling
$cmdWrapper = "@echo off
ssh -o StrictHostKeyChecking=no $SSHUser@$ServerIP ulmemory %*"
$cmdWrapper | Set-Content "$scriptsDir\ulmemory.cmd" -Encoding ASCII

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║          Installation Complete!                  ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Server: $SSHUser@$ServerIP" -ForegroundColor Cyan
Write-Host "Mode: SSH Remote Execution" -ForegroundColor Cyan
Write-Host ""
Write-Host "Usage:" -ForegroundColor Yellow
Write-Host "  ulmemory add `"my memory`"       -> SSH to server and add memory"
Write-Host "  ulmemory query `"search`"        -> Query on remote server"
Write-Host "  ulmemory status                  -> Show remote status"
Write-Host "  ulmemory up                      -> Start services on server"
Write-Host "  ulmemory memory add `"text`"      -> Add memory"
Write-Host "  ulmemory memory query `"term`"   -> Query memory"
Write-Host ""
Write-Host "Restart PowerShell or run: . `$PROFILE" -ForegroundColor Gray
Write-Host ""
