# This script contains shared functions used by both start_bot.ps1 and maintain_bot.ps1.

# --- Function to invoke the Python Virtual Environment setup ---
function Invoke-VenvSetup {
    param(
        [string]$ScriptRoot
    )
    $venvPath = Join-Path -Path $ScriptRoot -ChildPath "venv"
    $pythonExecutable = Join-Path -Path $venvPath -ChildPath "Scripts\python.exe"

    if (-not (Test-Path -Path $pythonExecutable)) {
        Write-Host "Python virtual environment not found. Creating one now..." -ForegroundColor Yellow
        # Ensure python command is available
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            Write-Host "Error: 'python' command not found. Cannot create virtual environment." -ForegroundColor Red
            Write-Host "Please ensure Python is installed and in your system's PATH." -ForegroundColor Yellow
            Read-Host "Press Enter to exit."
            exit 1
        }
        python -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to create the Python virtual environment." -ForegroundColor Red
            Read-Host "Press Enter to exit."
            exit 1
        }
        
        # Verify that the virtual environment was actually created
        if (-not (Test-Path -Path $pythonExecutable)) {
            Write-Host "Virtual environment creation appeared to succeed but python.exe not found." -ForegroundColor Red
            Write-Host "Check permissions and path length limits." -ForegroundColor Yellow
            Read-Host "Press Enter to exit."
            exit 1
        }
    }

    Write-Host "Installing/updating Python dependencies from requirements.txt..."
    & $pythonExecutable -m pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install dependencies. Check requirements.txt and internet connection." -ForegroundColor Yellow
    } else {
        Write-Host "Dependencies are up to date."
    }

    return $pythonExecutable
}