# VerveStacks Dashboard - Stop All Services
# Gracefully stops all running services

Write-Host "========================================" -ForegroundColor Red
Write-Host "   VerveStacks Dashboard - Service Stopper" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""

# Set window title
$Host.UI.RawUI.WindowTitle = "VerveStacks Dashboard - Service Stopper"

Write-Host "🔄 Stopping all services..." -ForegroundColor Yellow
Write-Host ""

# Stop Python service (port 5000)
try {
    $pythonProcess = Get-Process | Where-Object {$_.ProcessName -eq "python" -and $_.CommandLine -like "*api_server.py*"}
    if ($pythonProcess) {
        Write-Host "🛑 Stopping Python service..." -ForegroundColor Red
        Stop-Process -Id $pythonProcess.Id -Force
        Write-Host "✅ Python service stopped" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  Python service not running" -ForegroundColor Gray
    }
} catch {
    Write-Host "⚠️  Error stopping Python service: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Stop Node.js backend (port 3001)
try {
    $backendProcess = Get-Process | Where-Object {$_.ProcessName -eq "node" -and $_.CommandLine -like "*server.js*"}
    if ($backendProcess) {
        Write-Host "🛑 Stopping Backend service..." -ForegroundColor Red
        Stop-Process -Id $backendProcess.Id -Force
        Write-Host "✅ Backend service stopped" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  Backend service not running" -ForegroundColor Gray
    }
} catch {
    Write-Host "⚠️  Error stopping Backend service: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Stop React frontend (port 3000)
try {
    $frontendProcess = Get-Process | Where-Object {$_.ProcessName -eq "node" -and $_.CommandLine -like "*react-scripts*"}
    if ($frontendProcess) {
        Write-Host "🛑 Stopping Frontend service..." -ForegroundColor Red
        Stop-Process -Id $frontendProcess.Id -Force
        Write-Host "✅ Frontend service stopped" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  Frontend service not running" -ForegroundColor Gray
    }
} catch {
    Write-Host "⚠️  Error stopping Frontend service: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🔍 Checking if ports are free..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Check port status
$ports = @(3000, 3001, 5000)
foreach ($port in $ports) {
    $portStatus = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($portStatus) {
        Write-Host "⚠️  Port $port still in use" -ForegroundColor Yellow
    } else {
        Write-Host "✅ Port $port is free" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "🎉 All services stopped successfully!" -ForegroundColor Green
Write-Host ""
# Write-Host "Press any key to close this window" -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')