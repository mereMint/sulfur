$dbExists = $false
try {
    $testScript = @"
from dotenv import load_dotenv
"@
    Write-Host "Success"
} catch {
    Write-Host "Error"
}
