# Ultramemory CLI Installer for Windows PowerShell
# Run with: powershell -ExecutionPolicy Bypass -File install-cli.ps1

$ErrorActionPreference = "Stop"

Write-Host "Installing Ultramemory CLI..." -ForegroundColor Cyan

# Check Python version
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Host "Error: Python 3.11+ is required" -ForegroundColor Red
    exit 1
}

$pythonVersion = & python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
$requiredVersion = "3.11"

if ([version]$pythonVersion -lt [version]$requiredVersion) {
    Write-Host "Error: Python $requiredVersion or higher is required. Found: $pythonVersion" -ForegroundColor Red
    exit 1
}

Write-Host "Python version: $pythonVersion"

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

Write-Host "Config directory: $configDir"

# Check if we're in a virtual environment
if ($null -eq $env:VIRTUAL_ENV) {
    Write-Host "Creating virtual environment..."
    $venvDir = "$configDir\venv"

    if (Test-Path $venvDir) {
        Write-Host "Using existing virtual environment: $venvDir"
    } else {
        python -m venv $venvDir
        Write-Host "Virtual environment created at $venvDir"
    }
} else {
    Write-Host "Using existing virtual environment: $env:VIRTUAL_ENV"
    $venvDir = $env:VIRTUAL_ENV
}

# Upgrade pip
Write-Host "Upgrading pip..."
& "$venvDir\Scripts\pip.exe" install --upgrade pip

# Install package in editable mode
Write-Host "Installing ultramemory package..."
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $scriptDir
try {
    & "$venvDir\Scripts\pip.exe" install -e .
} finally {
    Pop-Location
}

# Create default settings if not exists
$settingsFile = "$configDir\settings.json"
if (-not (Test-Path $settingsFile)) {
    $settingsJson = @{
        mode = "local"
        services = @{
            api = "http://localhost:8000"
            graphiti = "http://localhost:8001"
            qdrant = "http://localhost:6333"
            redis = "localhost:6379"
            falkordb = "localhost:6370"
            postgres = "localhost:5432"
            grafana = "http://localhost:3000"
            prometheus = "http://localhost:9090"
        }
        credentials = @{
            postgres = @{ user = "postgres"; pass = "postgres" }
            grafana = @{ user = "admin"; pass = "admin" }
            qdrant = @{ api_key = "" }
            redis = @{ password = "" }
        }
        llm_provider = "openai"
        embedding_provider = "openai"
        researcher_topics = @()
        researcher_schedule = "daily"
        researcher_output_dir = "./researches"
    }

    $settingsJson | ConvertTo-Json -Depth 10 | Set-Content -Path $settingsFile -Encoding UTF8
    Write-Host "Default settings created at $settingsFile"
}

# Create wrapper script for easy access
Write-Host "Creating wrapper script..."

$scriptsDir = "$env:USERPROFILE\AppData\Local\Programs\ulmemory\Scripts"
if (-not (Test-Path $scriptsDir)) {
    New-Item -ItemType Directory -Path $scriptsDir -Force | Out-Null
}

$wrapperFile = "$scriptsDir\ulmemory.cmd"
$ps1Wrapper = "$scriptsDir\ulmemory.ps1"

# Create CMD wrapper
@"
@echo off
"%~dp0..\venv\Scripts\python.exe" -m ultramemory_cli.main %*
"@ | Set-Content -Path $wrapperFile -Encoding ASCII

# Create PowerShell wrapper function
@"
# Ultramemory CLI wrapper
function ulmemory {
    & "$venvDir\Scripts\python.exe" -m ultramemory_cli.main @args
}
Set-Alias -Name ulmemory -Value "$venvDir\Scripts\ulmemory.exe" -Scope Global -ErrorAction SilentlyContinue
"@ | Set-Content -Path "$configDir\ulmemory_profile.ps1" -Encoding UTF8

# Add to PowerShell profile
$profilePath = $PROFILE
$profileDir = Split-Path -Parent $profilePath

if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}

$profileEntry = @"

# Ultramemory CLI
. "$configDir\ulmemory_profile.ps1"
"@

if (-not (Test-Path $profilePath)) {
    $profileEntry | Set-Content -Path $profilePath -Encoding UTF8
} else {
    $existingContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
    if ($existingContent -notmatch "ulmemory_profile\.ps1") {
        Add-Content -Path $profilePath -Value $profileEntry
    }
}

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To use ultramemory:" -ForegroundColor Yellow
Write-Host "  1. Restart PowerShell or run: . `$PROFILE"
Write-Host "  2. Run: ulmemory --help"
Write-Host ""
Write-Host "Or use directly:"
Write-Host "  $venvDir\Scripts\ulmemory.exe --help"
Write-Host "  python -m ultramemory_cli.main --help"
