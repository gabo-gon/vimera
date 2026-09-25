```powershell
# VIMERA Windows installation script
#
# Creates a local Python virtual environment and installs
# VIMERA in editable mode.
#
# Supported Python versions:
#   Python 3.11 - 3.14
#
# Usage from PowerShell:
#
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\INSTALL.ps1
#
# Conda is not required.

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " VIMERA installation" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------
# Check Python
# ------------------------------------------------------------

Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue

if (-not $pythonCommand) {
    Write-Host ""
    Write-Host "ERROR: Python was not found on PATH." -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Python 3.11, 3.12, 3.13, or 3.14."
    Write-Host "Then restart PowerShell and run this installer again."
    exit 1
}

$pythonVersionOutput = & python --version

if ($LASTEXITCODE -ne 0) {
    throw "Unable to execute Python."
}

Write-Host "Found: $pythonVersionOutput" -ForegroundColor Green

# Extract major/minor version.
$versionMatch = [regex]::Match(
    $pythonVersionOutput,
    "Python\s+(\d+)\.(\d+)"
)

if (-not $versionMatch.Success) {
    throw "Unable to determine Python version."
}

$pythonMajor = [int]$versionMatch.Groups[1].Value
$pythonMinor = [int]$versionMatch.Groups[2].Value

if (
    $pythonMajor -ne 3 -or
    $pythonMinor -lt 11 -or
    $pythonMinor -ge 15
) {
    Write-Host ""
    Write-Host "ERROR: Unsupported Python version." -ForegroundColor Red
    Write-Host ""
    Write-Host "VIMERA requires Python >=3.11 and <3.15."
    Write-Host "Detected: $pythonVersionOutput"
    exit 1
}

Write-Host "Python version is supported." -ForegroundColor Green

# ------------------------------------------------------------
# Check project root
# ------------------------------------------------------------

Write-Host ""
Write-Host "[2/5] Checking VIMERA project..." -ForegroundColor Yellow

if (-not (Test-Path "pyproject.toml")) {
    Write-Host ""
    Write-Host "ERROR: pyproject.toml was not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Run this script from the VIMERA project root."
    exit 1
}

if (-not (Test-Path "src\vimera")) {
    Write-Host ""
    Write-Host "ERROR: VIMERA source directory was not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Expected:"
    Write-Host "  src\vimera"
    exit 1
}

Write-Host "VIMERA project detected." -ForegroundColor Green

# ------------------------------------------------------------
# Create virtual environment
# ------------------------------------------------------------

Write-Host ""
Write-Host "[3/5] Creating Python virtual environment..." -ForegroundColor Yellow

$venvPath = Join-Path (Get-Location) ".venv"

if (Test-Path $venvPath) {
    Write-Host "Existing .venv detected." -ForegroundColor Green
    Write-Host "Reusing existing environment."
}
else {
    & python -m venv $venvPath

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create the Python virtual environment."
    }

    Write-Host "Created .venv." -ForegroundColor Green
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment Python executable was not created."
}

# ------------------------------------------------------------
# Install VIMERA
# ------------------------------------------------------------

Write-Host ""
Write-Host "[4/5] Installing VIMERA and dependencies..." -ForegroundColor Yellow

& $venvPython -m pip install --upgrade pip

if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip."
}

& $venvPython -m pip install -e .

if ($LASTEXITCODE -ne 0) {
    throw "Failed to install VIMERA."
}

Write-Host "VIMERA installation completed." -ForegroundColor Green

# ------------------------------------------------------------
# Verify installation
# ------------------------------------------------------------

Write-Host ""
Write-Host "[5/5] Verifying installation..." -ForegroundColor Yellow

& $venvPython -c "import vimera; print('VIMERA Python package: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "VIMERA could not be imported after installation."
}

$vimeraExecutable = Join-Path $venvPath "Scripts\vimera.exe"

if (-not (Test-Path $vimeraExecutable)) {
    throw "VIMERA command-line executable was not created."
}

& $vimeraExecutable --help

if ($LASTEXITCODE -ne 0) {
    throw "VIMERA command-line interface failed verification."
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " VIMERA installation completed!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Python environment:"
Write-Host "  $venvPath"
Write-Host ""

Write-Host "Activate the environment:"
Write-Host ""
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host ""

Write-Host "Run VIMERA:"
Write-Host ""
Write-Host "  vimera --help" -ForegroundColor Cyan
Write-Host ""

Write-Host "Installation finished."
```
