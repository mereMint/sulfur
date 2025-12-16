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

Write-Host "Script content: $testScript"
