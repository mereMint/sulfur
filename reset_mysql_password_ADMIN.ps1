# Run this script AS ADMINISTRATOR
# Right-click PowerShell -> Run as Administrator

Write-Host "=== MySQL Root Password Reset ===" -ForegroundColor Cyan
Write-Host ""

# Stop MySQL
Write-Host "Stopping MySQL service..." -ForegroundColor Yellow
Stop-Service MySQL84

# Create init file
Write-Host "Creating password reset file..." -ForegroundColor Yellow
$initContent = "ALTER USER 'root'@'localhost' IDENTIFIED BY 'temp123';"
Set-Content -Path "C:\mysql-init.txt" -Value $initContent

# Start with init file
Write-Host "Starting MySQL with password reset..." -ForegroundColor Yellow
$mysqlPath = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe"

Start-Process -FilePath $mysqlPath -ArgumentList "--init-file=C:\mysql-init.txt" -NoNewWindow

# Wait for MySQL to process the init file
Write-Host "Waiting for password reset (10 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Stop the temporary process
Write-Host "Stopping temporary MySQL process..." -ForegroundColor Yellow
Stop-Process -Name mysqld -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Clean up
Write-Host "Cleaning up..." -ForegroundColor Yellow
Remove-Item "C:\mysql-init.txt" -ErrorAction SilentlyContinue

# Start service normally
Write-Host "Starting MySQL service..." -ForegroundColor Yellow
Start-Service MySQL84
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=== Password Reset Complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "New root password: temp123" -ForegroundColor White
Write-Host ""
Write-Host "Now run (in normal PowerShell):" -ForegroundColor Cyan
Write-Host "  cd C:\sulfur" -ForegroundColor White
Write-Host "  python setup_wizard.py" -ForegroundColor White
Write-Host ""
Write-Host "When prompted for root password, enter: temp123" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to exit"
