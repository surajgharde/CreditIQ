# Start the CreditIQ frontend development server (Windows)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $ScriptDir "frontend"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starting CreditIQ Frontend (React + Vite)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Frontend directory: $FrontendDir"
Write-Host "Dev server will be available at: http://localhost:5173"
Write-Host "Backend API proxy: http://localhost:8000"
Write-Host ""
Write-Host "Press Ctrl+C to stop the server"
Write-Host ""

Set-Location $FrontendDir
npm run dev
npm run build
