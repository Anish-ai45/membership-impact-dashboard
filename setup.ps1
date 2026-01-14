# Setup script for Membership Impact Chatbot (Windows PowerShell)
# This script creates and activates a virtual environment, then installs dependencies

Write-Host "Setting up Membership Impact Chatbot..." -ForegroundColor Cyan

# Check if virtual environment already exists
if (Test-Path ".venv") {
    Write-Host "Virtual environment already exists." -ForegroundColor Yellow
    $recreate = Read-Host "Do you want to recreate it? (y/N)"
    if ($recreate -eq "y" -or $recreate -eq "Y") {
        Write-Host "Removing existing virtual environment..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force .venv
    } else {
        Write-Host "Using existing virtual environment." -ForegroundColor Green
        & .\.venv\Scripts\Activate.ps1
        Write-Host "Virtual environment activated." -ForegroundColor Green
        Write-Host "Installing/updating dependencies..." -ForegroundColor Cyan
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        Write-Host "Setup complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "To activate the virtual environment in the future, run:" -ForegroundColor Cyan
        Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
        exit 0
    }
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Cyan
python -m venv .venv

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Virtual environment is now activated." -ForegroundColor Cyan
Write-Host "To activate it in the future, run:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To run the app:" -ForegroundColor Cyan
Write-Host "  python app/dashboard.py" -ForegroundColor White
Write-Host "  # Or use: .\run_dashboard.sh" -ForegroundColor White
