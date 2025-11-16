# Test script for new features
Write-Host "`n=== Sulfur Bot - Feature Test Script ===" -ForegroundColor Cyan
Write-Host "Testing newly implemented features...`n" -ForegroundColor Cyan

$ErrorCount = 0
$SuccessCount = 0

# Test 1: Python Syntax Check
Write-Host "[1/6] Testing Python syntax..." -ForegroundColor Yellow
$files = @(
    "modules\werwolf.py",
    "modules\db_helpers.py", 
    "modules\api_helpers.py",
    "modules\emoji_manager.py",
    "bot.py",
    "web_dashboard.py"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        python -m py_compile $file 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ $file" -ForegroundColor Green
            $SuccessCount++
        } else {
            Write-Host "  ✗ $file - SYNTAX ERROR" -ForegroundColor Red
            $ErrorCount++
        }
    } else {
        Write-Host "  ⚠ $file - NOT FOUND" -ForegroundColor Yellow
    }
}

# Test 2: Check Database Migration File
Write-Host "`n[2/6] Checking database migration..." -ForegroundColor Yellow
if (Test-Path "scripts\db_migrations\002_medium_priority_features.sql") {
    Write-Host "  ✓ Migration file exists" -ForegroundColor Green
    $content = Get-Content "scripts\db_migrations\002_medium_priority_features.sql" -Raw
    $tables = @("wrapped_registrations", "emoji_descriptions", "conversation_context", "ai_model_usage")
    foreach ($table in $tables) {
        if ($content -match $table) {
            Write-Host "  ✓ Table '$table' defined" -ForegroundColor Green
            $SuccessCount++
        } else {
            Write-Host "  ✗ Table '$table' missing" -ForegroundColor Red
            $ErrorCount++
        }
    }
} else {
    Write-Host "  ✗ Migration file not found" -ForegroundColor Red
    $ErrorCount++
}

# Test 3: Verify New Functions in db_helpers
Write-Host "`n[3/6] Checking database helper functions..." -ForegroundColor Yellow
$required_functions = @(
    "register_for_wrapped",
    "unregister_from_wrapped",
    "is_registered_for_wrapped",
    "save_emoji_description",
    "get_emoji_description",
    "save_conversation_context",
    "get_conversation_context",
    "track_ai_model_usage",
    "get_ai_usage_stats"
)

$db_content = Get-Content "modules\db_helpers.py" -Raw
foreach ($func in $required_functions) {
    if ($db_content -match "async def $func") {
        Write-Host "  ✓ Function '$func' found" -ForegroundColor Green
        $SuccessCount++
    } else {
        Write-Host "  ✗ Function '$func' missing" -ForegroundColor Red
        $ErrorCount++
    }
}

# Test 4: Verify API Helper Functions
Write-Host "`n[4/6] Checking API helper functions..." -ForegroundColor Yellow
$api_functions = @(
    "get_vision_analysis",
    "get_ai_response_with_model",
    "get_emoji_description"
)

$api_content = Get-Content "modules\api_helpers.py" -Raw
foreach ($func in $api_functions) {
    if ($api_content -match "async def $func") {
        Write-Host "  ✓ Function '$func' found" -ForegroundColor Green
        $SuccessCount++
    } else {
        Write-Host "  ✗ Function '$func' missing" -ForegroundColor Red
        $ErrorCount++
    }
}

# Test 5: Verify Emoji Manager Module
Write-Host "`n[5/6] Checking emoji manager..." -ForegroundColor Yellow
if (Test-Path "modules\emoji_manager.py") {
    Write-Host "  ✓ emoji_manager.py exists" -ForegroundColor Green
    $emoji_content = Get-Content "modules\emoji_manager.py" -Raw
    $emoji_functions = @("analyze_server_emojis", "get_emoji_context_for_ai")
    foreach ($func in $emoji_functions) {
        if ($emoji_content -match "async def $func") {
            Write-Host "  ✓ Function '$func' found" -ForegroundColor Green
            $SuccessCount++
        } else {
            Write-Host "  ✗ Function '$func' missing" -ForegroundColor Red
            $ErrorCount++
        }
    }
} else {
    Write-Host "  ✗ emoji_manager.py not found" -ForegroundColor Red
    $ErrorCount++
}

# Test 6: Check Documentation
Write-Host "`n[6/6] Checking documentation..." -ForegroundColor Yellow
$docs = @(
    "docs\MEDIUM_PRIORITY_FEATURES.md",
    "docs\IMPLEMENTATION_SUMMARY.md",
    "TODO.md"
)

foreach ($doc in $docs) {
    if (Test-Path $doc) {
        Write-Host "  ✓ $doc exists" -ForegroundColor Green
        $SuccessCount++
    } else {
        Write-Host "  ✗ $doc missing" -ForegroundColor Red
        $ErrorCount++
    }
}

# Summary
Write-Host "`n" -NoNewline
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "              Test Summary                  " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

Write-Host "`nPassed: $SuccessCount" -ForegroundColor Green
Write-Host "Failed: $ErrorCount" -ForegroundColor Red

if ($ErrorCount -eq 0) {
    Write-Host "`nAll tests passed! Features are ready for integration." -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nSome tests failed. Please review the output above." -ForegroundColor Yellow
    exit 1
}
