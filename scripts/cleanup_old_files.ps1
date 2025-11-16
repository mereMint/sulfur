# Cleanup utility for old logs and backups
# This script removes files older than the specified number of days

param(
    [int]$DaysToKeep = 7
)

Write-Host "=== Sulfur Bot Cleanup Utility ===" -ForegroundColor Cyan
Write-Host "Removing files older than $DaysToKeep days..." -ForegroundColor Yellow
Write-Host ""

$cleanupDate = (Get-Date).AddDays(-$DaysToKeep)

# Clean up old log files
Write-Host "Checking logs directory..." -ForegroundColor Gray
$logPath = Join-Path -Path $PSScriptRoot -ChildPath "logs"
if (Test-Path -Path $logPath) {
    $oldLogs = Get-ChildItem -Path $logPath -Filter "*.log" | Where-Object { $_.LastWriteTime -lt $cleanupDate }
    if ($oldLogs) {
        $oldLogs | ForEach-Object {
            Write-Host "  [LOG] Deleting: $($_.Name)" -ForegroundColor Yellow
            Remove-Item $_.FullName -Force
        }
        Write-Host "  Removed $($oldLogs.Count) old log file(s)" -ForegroundColor Green
    } else {
        Write-Host "  No old log files to remove" -ForegroundColor Green
    }
} else {
    Write-Host "  Logs directory not found" -ForegroundColor Gray
}

Write-Host ""

# Clean up old backup files
Write-Host "Checking backups directory..." -ForegroundColor Gray
$backupPath = Join-Path -Path $PSScriptRoot -ChildPath "backups"
if (Test-Path -Path $backupPath) {
    $oldBackups = Get-ChildItem -Path $backupPath -Filter "*.sql" | Where-Object { $_.LastWriteTime -lt $cleanupDate }
    if ($oldBackups) {
        # Calculate total size of files to be deleted
        $totalSize = ($oldBackups | Measure-Object -Property Length -Sum).Sum / 1MB
        
        $oldBackups | ForEach-Object {
            $sizeMB = [math]::Round($_.Length / 1MB, 2)
            Write-Host "  [BACKUP] Deleting: $($_.Name) ($sizeMB MB)" -ForegroundColor Yellow
            Remove-Item $_.FullName -Force
        }
        Write-Host "  Removed $($oldBackups.Count) old backup file(s) (Total: $([math]::Round($totalSize, 2)) MB freed)" -ForegroundColor Green
    } else {
        Write-Host "  No old backup files to remove" -ForegroundColor Green
    }
} else {
    Write-Host "  Backups directory not found" -ForegroundColor Gray
}

Write-Host ""

# Clean up temporary flag files
Write-Host "Checking for stale flag files..." -ForegroundColor Gray
$flagFiles = @("stop.flag", "restart.flag", "update_pending.flag")
$removedFlags = 0
foreach ($flag in $flagFiles) {
    $flagPath = Join-Path -Path $PSScriptRoot -ChildPath $flag
    if (Test-Path -Path $flagPath) {
        Write-Host "  [FLAG] Removing stale flag: $flag" -ForegroundColor Yellow
        Remove-Item $flagPath -Force
        $removedFlags++
    }
}
if ($removedFlags -eq 0) {
    Write-Host "  No stale flag files found" -ForegroundColor Green
} else {
    Write-Host "  Removed $removedFlags stale flag file(s)" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Cleanup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run this cleanup automatically, add it to your scheduled tasks or cron job." -ForegroundColor Gray
Write-Host "Example: .\cleanup_old_files.ps1 -DaysToKeep 7" -ForegroundColor Gray
