#!/bin/bash
#       RSRSRSRSba   RSRSRSRSRS8  RS  RSRSRSRSba,
#       RS      "8b  RS           RS  RS      `"8b
#       RS      ,8P  RS           RS  RS        `8b
#       RSaaaaaa8P'  RSaaaaa      RS  RS         RS
#       RS""""RS'    RS"""""      RS  RS         RS
#       RS    `8b    RS           RS  RS         8P
#       RS     `8b   RS           RS  RS      .a8P
#       RS      `8b  RSRSRSRSRS8  RS  RSRSRSRSY"'
#
#        adRSRS8ba   RS        RS  RSRSRSRSba   RSb           dRS  RSRSRSRSRS8  RS  RSRSRSRSRS8  RSRSRSRSba
#       d8"     "8b  RS        RS  RS      "8b  RS8b         dRS8  RS           RS  RS           RS      "8b
#       Y8,          RS        RS  RS      ,8P  RS`8b       d8'RS  RS           RS  RS           RS      ,8P
#       `Y8aaaaa,    RS        RS  RSaaaaaa8P'  RS `8b     d8' RS  RSaaaaa      RS  RSaaaaa      RSaaaaaa8P'
#         `"""""8b,  RS        RS  RS""""RS'    RS  `8b   d8'  RS  RS"""""      RS  RS"""""      RS""""RS'
#               `8b  RS        RS  RS    `8b    RS   `8b d8'   RS  RS           RS  RS           RS    `8b
#       Y8a     a8P  Y8a.    .a8P  RS     `8b   RS    `RS8'    RS  RS           RS  RS           RS     `8b
#        "YRSRS8P"    `"YRSRSY"'   RS      `8b  RS     `8'     RS  RSRSRSRSRS8  RS  RSRSRSRSRS8  RS      `8b
#
#        I8,        8        ,8I  RSRSRSRSRSRS  RSRSRSRSRS8
#        `8b       d8b       d8'       RS       RS
#         "8,     ,8"8,     ,8"        RS       RS
#          Y8     8P Y8     8P         RS       RSaaaaa
#          `8b   d8' `8b   d8'         RS       RS"""""
#           `8a a8'   `8a a8'          RS       RS
#       RS8  `8a8'     `8a8'           RS       RS
#       RS8   `8'       `8'            RS       RS
#
# Author:  Reid Surmeier
# Client:  Clement Valla
# Date:    2026 Feb 16th
#
# Installation script for matrix-controller

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Matrix Controller Installation Script"
echo "====================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python 3.11 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python version check passed: $PYTHON_VERSION"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install gpiozero pyyaml

# Check for lgpio (should be available on Pi 5)
if ! python3 -c "import lgpio" 2>/dev/null; then
    echo "Warning: lgpio module not found. Installing..."
    apt-get update
    apt-get install -y python3-lgpio
fi

echo "✓ Python dependencies installed"

# Create configuration directory
echo ""
echo "Creating configuration directory..."
mkdir -p /etc/matrix-controller

# Copy configuration file if it doesn't exist
if [ ! -f /etc/matrix-controller/controller.yaml ]; then
    cp "$PROJECT_ROOT/config/controller.yaml" /etc/matrix-controller/controller.yaml
    echo "✓ Configuration file installed: /etc/matrix-controller/controller.yaml"
    echo "  Please review and adjust GPIO pins as needed"
else
    echo "✓ Configuration file already exists (not overwritten)"
fi

# Install Python package
echo ""
echo "Installing Python package..."
PYTHON_SITE_PACKAGES=$(python3 -c "import site; print(site.getsitepackages()[0])")
CONTROLLER_DIR="$PYTHON_SITE_PACKAGES/controller"

mkdir -p "$CONTROLLER_DIR"
cp -r "$PROJECT_ROOT/src/controller"/* "$CONTROLLER_DIR/"
echo "✓ Python package installed to $CONTROLLER_DIR"

# Install systemd service
echo ""
echo "Installing systemd service..."
cp "$PROJECT_ROOT/systemd/matrix-controller.service" /etc/systemd/system/
systemctl daemon-reload
echo "✓ Systemd service installed"

# Enable service (but don't start yet - user should configure first)
echo ""
echo "Enabling matrix-controller service..."
systemctl enable matrix-controller.service
echo "✓ Service enabled (will start on boot)"

echo ""
echo "====================================="
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Review and edit /etc/matrix-controller/controller.yaml"
echo "2. Ensure your GPIO wiring matches the configuration"
echo "3. Test with: sudo systemctl start matrix-controller"
echo "4. Check logs with: journalctl -u matrix-controller -f"
echo "5. Test dry-run mode: python3 -m controller.main --config /etc/matrix-controller/controller.yaml --dry-run"
echo ""
