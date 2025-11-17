# ============================================================
# Script Testing Utility for Sulfur Bot
# ============================================================

$ErrorActionPreference = 'Continue'

Write-Host "Testing Sulfur Bot Scripts" -ForegroundColor Cyan
Write-Host ""

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

$psScripts = @(
    "setup_mysql.ps1",
    "start.ps1",
    "quick_setup.ps1",
    "maintain_bot.ps1"
)

$totalTests = 0
$passedTests = 0

Write-Host "Testing PowerShell Scripts:" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

foreach ($script in $psScripts) {
    if (Test-Path $script) {
        $totalTests++
        Write-Host "  $script..." -NoNewline
        
        try {
            $errors = @()
            $tokens = @()
            $ast = [System.Management.Automation.Language.Parser]::ParseFile(
                (Join-Path $scriptPath $script),
                [ref]$tokens,
                [ref]$errors
            )
            
            if ($errors.Count -eq 0) {
                Write-Host " OK" -ForegroundColor Green
                $passedTests++
            } else {
                Write-Host " ERROR" -ForegroundColor Red
                foreach ($error in $errors) {
                    Write-Host "    Line $($error.Extent.StartLineNumber): $($error.Message)" -ForegroundColor Yellow
                }
            }
        } catch {
            Write-Host " FAILED: $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "Testing Critical Files:" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

$criticalFiles = @(
    ".env",
    "config\config.json",
    "config\system_prompt.txt",
    "requirements.txt",
    "setup_database.sql",
    "bot.py",
    "web_dashboard.py"
)

foreach ($file in $criticalFiles) {
    $totalTests++
    Write-Host "  $file..." -NoNewline
    if (Test-Path $file) {
        Write-Host " OK" -ForegroundColor Green
        $passedTests++
    } else {
        Write-Host " NOT FOUND" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Total: $totalTests" -ForegroundColor White
Write-Host "  Passed: $passedTests" -ForegroundColor Green
Write-Host "  Failed: $($totalTests - $passedTests)" -ForegroundColor $(if ($totalTests -eq $passedTests) { "Green" } else { "Red" })
Write-Host ""

if ($totalTests -eq $passedTests) {
    Write-Host "All tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some tests failed." -ForegroundColor Red
    exit 1
}
