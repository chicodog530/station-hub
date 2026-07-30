# Station Hub Automated Installer

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Station Hub Dependencies Installer" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check for Python
Write-Host "Checking for Python 3..."
$pythonExe = Get-Command python -ErrorAction SilentlyContinue

if ($null -eq $pythonExe) {
    Write-Host "Python is not installed or not in PATH." -ForegroundColor Yellow
    Write-Host "Downloading the official Python 3.11 Installer from python.org..." -ForegroundColor Cyan
    
    $installerPath = "$env:TEMP\python-3.11.9-amd64.exe"
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $installerPath
    
    Write-Host "Installing Python 3.11 silently... (This may take a minute and may ask for Admin permissions)" -ForegroundColor Cyan
    
    # Run the installer silently, add to PATH, and install for all users
    $installArgs = "/quiet InstallAllUsers=1 PrependPath=1"
    Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -Verb RunAs
    
    Write-Host "Python installation complete!" -ForegroundColor Green
    
    # Reload environment variables so the current script can see Python in the PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "Python is already installed!" -ForegroundColor Green
}

# 2. Verify Python is now accessible
$pythonExe = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $pythonExe) {
    Write-Host "Error: Python was installed but is still not accessible in the PATH." -ForegroundColor Red
    Write-Host "Please restart your computer and try again." -ForegroundColor Red
    exit
}

# 3. Install Dependencies
Write-Host "`nInstalling required Python libraries from requirements.txt..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "   Installation Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "You can now start the Hub by double-clicking run.bat!"
Write-Host ""
