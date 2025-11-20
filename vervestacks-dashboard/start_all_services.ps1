# VerveStacks Dashboard - Start All Services
# Simple PowerShell script to start all three services

# Set window title for the orchestrator
$Host.UI.RawUI.WindowTitle = "VerveStacks Dashboard - Service Manager"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   VerveStacks Dashboard - Service Manager" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "Script location: $scriptDir" -ForegroundColor Cyan

# Check required directories
$pythonDir = Join-Path $scriptDir "python-service"
$backendDir = Join-Path $scriptDir "backend"
$frontendDir = Join-Path $scriptDir "frontend"
$venvPython = Join-Path $pythonDir ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonDir)) {
    Write-Host "ERROR: python-service directory not found!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $backendDir)) {
    Write-Host "ERROR: backend directory not found!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $frontendDir)) {
    Write-Host "ERROR: frontend directory not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Project structure validated successfully" -ForegroundColor Green
Write-Host ""

# Check if dependencies are installed
$backendNodeModules = Join-Path $backendDir "node_modules"
$frontendNodeModules = Join-Path $frontendDir "node_modules"

if (-not (Test-Path $backendNodeModules) -or -not (Test-Path $frontendNodeModules)) {
    Write-Host "Dependencies not found. Installing..." -ForegroundColor Yellow
    
    # Install backend dependencies
    Write-Host "Installing backend dependencies..." -ForegroundColor Blue
    Set-Location $backendDir
    npm install
    Set-Location $scriptDir
    
    # Install frontend dependencies
    Write-Host "Installing frontend dependencies..." -ForegroundColor Blue
    Set-Location $frontendDir
    npm install
    Set-Location $scriptDir
    
    Write-Host "All dependencies installed successfully!" -ForegroundColor Green
    Write-Host ""
}

Write-Host "Starting all services..." -ForegroundColor Yellow
Write-Host ""

# Start Python FastAPI service
Write-Host "Starting Python FastAPI service..." -ForegroundColor Green
$pythonCmd = "cd `"$pythonDir`"; & `"$venvPython`" api_server.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $pythonCmd -WindowStyle Normal
Start-Sleep -Seconds 3

# Start Node.js backend
Write-Host "Starting Node.js backend..." -ForegroundColor Green
$backendCmd = "cd '$backendDir'; `$env:NODE_ENV='development'; npm start"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal
Start-Sleep -Seconds 3

# Start React frontend
Write-Host "Starting React frontend..." -ForegroundColor Green
$frontendCmd = "cd '$frontendDir'; `$env:REACT_APP_ENV='development'; npm start"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "All services started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Checking service status..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Check if services are responding
try {
    $pythonHealth = Invoke-RestMethod -Uri "http://localhost:5000/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "Python Service: Healthy" -ForegroundColor Green
} catch {
    Write-Host "Python Service: Starting up..." -ForegroundColor Yellow
}

try {
    $backendHealth = Invoke-RestMethod -Uri "http://localhost:3001/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "Backend API: Healthy" -ForegroundColor Green
} catch {
    Write-Host "Backend API: Starting up..." -ForegroundColor Yellow
}

Write-Host "Frontend: Starting up..." -ForegroundColor Green
Write-Host ""
Write-Host "Services are running in separate windows:" -ForegroundColor White
Write-Host "+-------------------------------------------------------------+" -ForegroundColor DarkGray
Write-Host "| Python Service: http://localhost:5000                      |" -ForegroundColor Cyan
Write-Host "| Backend API:   http://localhost:3001                      |" -ForegroundColor Cyan
Write-Host "| Frontend:      http://localhost:3000                      |" -ForegroundColor Cyan
Write-Host "+-------------------------------------------------------------+" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Each service is running in its own PowerShell window." -ForegroundColor Yellow
Write-Host "Close those windows to stop individual services." -ForegroundColor Yellow
Write-Host ""
Write-Host "TIPS:" -ForegroundColor Magenta
Write-Host "Frontend will auto-open in your browser at http://localhost:3000" -ForegroundColor White
Write-Host "Test Python API: http://localhost:5000/health" -ForegroundColor White
Write-Host "Test Backend API: http://localhost:3001/health" -ForegroundColor White
Write-Host "Use Ctrl+C in individual service windows to stop them" -ForegroundColor White
Write-Host ""
Write-Host "Project paths used:" -ForegroundColor White
Write-Host "+-------------------------------------------------------------+" -ForegroundColor DarkGray
Write-Host "| Python:  $pythonDir" -ForegroundColor Cyan
Write-Host "| Backend: $backendDir" -ForegroundColor Cyan
Write-Host "| Frontend: $frontendDir" -ForegroundColor Cyan
Write-Host "+-------------------------------------------------------------+" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Press any key to close this window" -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
