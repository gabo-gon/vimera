```bash
#!/usr/bin/env bash

# VIMERA installation script
#
# Creates a local Python virtual environment and installs
# VIMERA in editable mode.
#
# Supported Python versions:
#   Python 3.11 - 3.14
#
# Usage:
#
#   chmod +x install.sh
#   ./install.sh
#
# Conda is not required.

set -euo pipefail

echo
echo "=========================================="
echo " VIMERA installation"
echo "=========================================="
echo

# ------------------------------------------------------------
# Check Python
# ------------------------------------------------------------

echo "[1/5] Checking Python..."

if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
else
    echo
    echo "ERROR: Python 3 was not found on PATH."
    echo
    echo "Install Python 3.11, 3.12, 3.13, or 3.14."
    exit 1
fi

PYTHON_VERSION="$("$PYTHON" --version 2>&1)"

echo "Found: $PYTHON_VERSION"

PYTHON_MAJOR="$("$PYTHON" -c 'import sys; print(sys.version_info.major)')"
PYTHON_MINOR="$("$PYTHON" -c 'import sys; print(sys.version_info.minor)')"

if [[ "$PYTHON_MAJOR" -ne 3 ||
      "$PYTHON_MINOR" -lt 11 ||
      "$PYTHON_MINOR" -ge 15 ]]; then

    echo
    echo "ERROR: Unsupported Python version."
    echo
    echo "VIMERA requires Python >=3.11 and <3.15."
    echo "Detected: $PYTHON_VERSION"
    exit 1
fi

echo "Python version is supported."

# ------------------------------------------------------------
# Check project root
# ------------------------------------------------------------

echo
echo "[2/5] Checking VIMERA project..."

if [[ ! -f "pyproject.toml" ]]; then
    echo
    echo "ERROR: pyproject.toml was not found."
    echo
    echo "Run this script from the VIMERA project root."
    exit 1
fi

if [[ ! -d "src/vimera" ]]; then
    echo
    echo "ERROR: VIMERA source directory was not found."
    echo
    echo "Expected:"
    echo "  src/vimera"
    exit 1
fi

echo "VIMERA project detected."

# ------------------------------------------------------------
# Create virtual environment
# ------------------------------------------------------------

echo
echo "[3/5] Creating Python virtual environment..."

VENV=".venv"

if [[ -d "$VENV" ]]; then
    echo "Existing .venv detected."
    echo "Reusing existing environment."
else
    "$PYTHON" -m venv "$VENV"
    echo "Created .venv."
fi

VENV_PYTHON="$VENV/bin/python"

if [[ ! -f "$VENV_PYTHON" ]]; then
    echo
    echo "ERROR: Virtual environment Python was not created."
    exit 1
fi

# ------------------------------------------------------------
# Install VIMERA
# ------------------------------------------------------------

echo
echo "[4/5] Installing VIMERA and dependencies..."

"$VENV_PYTHON" -m pip install --upgrade pip

"$VENV_PYTHON" -m pip install -e .

echo "VIMERA installation completed."

# ------------------------------------------------------------
# Verify installation
# ------------------------------------------------------------

echo
echo "[5/5] Verifying installation..."

"$VENV_PYTHON" -c "import vimera; print('VIMERA Python package: OK')"

"$VENV/bin/vimera" --help >/dev/null

echo "VIMERA command-line interface: OK"

echo
echo "=========================================="
echo " VIMERA installation completed!"
echo "=========================================="
echo

echo "Python environment:"
echo "  $VENV"
echo

echo "Activate the environment:"
echo
echo "  source .venv/bin/activate"
echo

echo "Run VIMERA:"
echo
echo "  vimera --help"
echo

echo "Installation finished."
```
