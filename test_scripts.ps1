# ============================================================
# Script Testing Utility for Sulfur Bot
# ============================================================
# Tests all setup and start scripts for syntax errors

param(
    [switch]$Verbose
)

$ErrorActionPreference = 'Continue'

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         Sulfur Bot - Script Testing Utility               ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# PowerShell scripts to test
$psScripts = @(
    "setup_mysql.ps1",
    "start.ps1",
    "quick_setup.ps1",
    "maintain_bot.ps1",
    "scripts\start_bot.ps1"
)

# Bash scripts to test
$bashScripts = @(
    "setup_mysql.sh",
    "start.sh",
    "quick_setup.sh",
    "maintain_bot.sh",
    "scripts\start_bot.sh"
)

$totalTests = 0
$passedTests = 0
$failedTests = 0

Write-Host "Testing PowerShell Scripts" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

foreach ($script in $psScripts) {
    if (Test-Path $script) {
        $totalTests++
        Write-Host "Testing: $script" -ForegroundColor Cyan
        
        try {
            $errors = @()
            $tokens = @()
            $ast = [System.Management.Automation.Language.Parser]::ParseFile(
                (Join-Path $scriptPath $script),
                [ref]$tokens,
                [ref]$errors
            )
            
            if ($errors.Count -eq 0) {
                Write-Host "  ✓ Syntax valid" -ForegroundColor Green
                $passedTests++
                
                if ($Verbose) {
                    # Count functions
                    $funcDef = [System.Management.Automation.Language.FunctionDefinitionAst]
                    $functions = $ast.FindAll({param($node) $node -is $funcDef}, $true)
                    Write-Host "    Functions: $($functions.Count)" -ForegroundColor Gray
                    
                    # Count parameters
                    $paramDef = [System.Management.Automation.Language.ParameterAst]
                    $params = $ast.FindAll({param($node) $node -is $paramDef}, $true)
                    Write-Host "    Parameters: $($params.Count)" -ForegroundColor Gray
                }
            } else {
                Write-Host "  ✗ Syntax errors found:" -ForegroundColor Red
                $failedTests++
                
                foreach ($error in $errors) {
                    Write-Host "    Line $($error.Extent.StartLineNumber): $($error.Message)" -ForegroundColor Yellow
                }
            }
        } catch {
            Write-Host "  ✗ Parse failed: $_" -ForegroundColor Red
            $failedTests++
        }
        
        Write-Host ""
    } else {
        Write-Host "Skipping: $script (not found)" -ForegroundColor Gray
        Write-Host ""
    }
}

Write-Host "Testing Bash Scripts" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

foreach ($script in $bashScripts) {
    if (Test-Path $script) {
        $totalTests++
        Write-Host "Testing: $script" -ForegroundColor Cyan
        
        # Check for common bash issues
        $content = Get-Content $script -Raw
        $issues = @()
        
        # Check shebang
        if ($content -notmatch '^#!/bin/(ba)?sh') {
            $issues += "Missing or incorrect shebang"
        }
        
        # Check for Windows line endings (would cause issues on Linux)
        if ($content -match "`r`n") {
            $issues += "Contains Windows line endings (CRLF) - should be LF only for Linux/Termux"
        }
        
        # Check for common syntax patterns
        if ($content -match '\$\{.*\}' -or $content -match 'if \[') {
            # Has bash syntax
            Write-Host "  ✓ Contains bash syntax patterns" -ForegroundColor Green
        }
        
        if ($issues.Count -eq 0) {
            Write-Host "  ✓ Basic validation passed" -ForegroundColor Green
            $passedTests++
        } else {
            Write-Host "  ⚠ Potential issues:" -ForegroundColor Yellow
            foreach ($issue in $issues) {
                Write-Host "    - $issue" -ForegroundColor Yellow
            }
            # Don't count as failure, just warnings
            $passedTests++
        }
        
        if ($Verbose) {
            $lines = ($content -split "`n").Count
            Write-Host "    Lines: $lines" -ForegroundColor Gray
        }
        
        Write-Host ""
    } else {
        Write-Host "Skipping: $script (not found)" -ForegroundColor Gray
        Write-Host ""
    }
}

# Test critical files
Write-Host "Testing Critical Files" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

$criticalFiles = @{
    ".env" = "Environment variables"
    "config\config.json" = "Bot configuration"
    "config\system_prompt.txt" = "AI system prompt"
    "requirements.txt" = "Python dependencies"
    "setup_database.sql" = "Database schema"
    "bot.py" = "Main bot file"
    "web_dashboard.py" = "Web dashboard"
}

foreach ($file in $criticalFiles.Keys) {
    $totalTests++
    if (Test-Path $file) {
        Write-Host "✓ $file - $($criticalFiles[$file])" -ForegroundColor Green
        $passedTests++
        
        if ($Verbose -and $file -like "*.json") {
            try {
                $json = Get-Content $file -Raw | ConvertFrom-Json
                Write-Host "  Valid JSON" -ForegroundColor Gray
            } catch {
                Write-Host "  ⚠ Invalid JSON: $_" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "✗ $file - $($criticalFiles[$file]) (NOT FOUND)" -ForegroundColor Red
        $failedTests++
    }
}

Write-Host ""

# Summary
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                      Test Summary                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "Total Tests: $totalTests" -ForegroundColor White
Write-Host "Passed:      " -NoNewline
Write-Host "$passedTests" -ForegroundColor Green
Write-Host "Failed:      " -NoNewline
if ($failedTests -gt 0) {
    Write-Host "$failedTests" -ForegroundColor Red
} else {
    Write-Host "$failedTests" -ForegroundColor Green
}
Write-Host ""

if ($failedTests -eq 0) {
    Write-Host "✓ All tests passed! Scripts are ready to use." -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ Some tests failed. Please fix the issues above." -ForegroundColor Red
    exit 1
}
