# Test the problematic section
Write-Host "Starting test..."

$dbExists = $false
try {
    # Try to connect to the database
    $testScript = @"
import mysql.connector
import os
from dotenv import load_dotenv
load_dotenv()
try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'sulfur_bot_user'),
        password=os.getenv('DB_PASS', ''),
        database=os.getenv('DB_NAME', 'sulfur_bot'),
        connection_timeout=5
    )
    conn.close()
    print('EXISTS')
except:
    print('NOT_EXISTS')
"@
    $testResult = python -c $testScript 2>&1
    $dbExists = $testResult -match "EXISTS"
} catch {
    $dbExists = $false
}

Write-Host "Test completed. dbExists = $dbExists"
