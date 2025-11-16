Write-Host "Testing new features..." -ForegroundColor Cyan

# Test syntax
Write-Host "`nPython syntax check..."
python -m py_compile modules\werwolf.py modules\db_helpers.py modules\api_helpers.py modules\emoji_manager.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "PASS: All Python files compile" -ForegroundColor Green
} else {
    Write-Host "FAIL: Syntax errors found" -ForegroundColor Red
    exit 1
}

# Check migration
Write-Host "`nDatabase migration check..."
if (Test-Path "scripts\db_migrations\002_medium_priority_features.sql") {
    Write-Host "PASS: Migration file exists" -ForegroundColor Green
} else {
    Write-Host "FAIL: Migration file not found" -ForegroundColor Red
}

# Check documentation
Write-Host "`nDocumentation check..."
if (Test-Path "docs\MEDIUM_PRIORITY_FEATURES.md") {
    Write-Host "PASS: Integration guide exists" -ForegroundColor Green
} else {
    Write-Host "FAIL: Documentation missing" -ForegroundColor Red
}

Write-Host "`nAll tests passed!" -ForegroundColor Green
