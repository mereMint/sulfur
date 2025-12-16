#!/bin/bash

# Test script to verify venv detection logic

echo "Testing venv detection and installation logic..."
echo ""
echo "=========================================="
echo "TEST 1: Check venv availability"
echo "=========================================="

PYTHON_CMD="python3"
if ! $PYTHON_CMD -m venv --help >/dev/null 2>&1; then
    echo "❌ venv not available"
    echo ""
    echo "Would attempt to install based on distribution..."
    
    # Detect Linux distribution
    if [ -f /etc/debian_version ]; then
        echo "Detected: Debian/Ubuntu"
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        echo "Python version: $PYTHON_VERSION"
        echo "Would run: sudo apt-get install -y python${PYTHON_VERSION}-venv python3-venv"
    elif [ -f /etc/redhat-release ]; then
        echo "Detected: RHEL/CentOS/Fedora"
        echo "Would run: sudo dnf install -y python3-venv"
    elif [ -f /etc/arch-release ]; then
        echo "Detected: Arch Linux"
        echo "Would run: sudo pacman -S --noconfirm python"
    else
        echo "Could not detect distribution"
    fi
else
    echo "✅ venv is available"
    echo ""
    echo "Python version:"
    $PYTHON_CMD --version
    echo ""
    echo "Virtual environment can be created with:"
    echo "  $PYTHON_CMD -m venv <path>"
fi

echo ""
echo "=========================================="
echo "TEST 2: Check distro detection"
echo "=========================================="
echo ""

if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "Distribution: $NAME"
    echo "Version: $VERSION"
fi

echo ""
echo "=========================================="
echo "TEST 3: Command availability"
echo "=========================================="
echo ""

for cmd in sudo python3 python apt dnf pacman pkg; do
    if command -v $cmd &> /dev/null; then
        echo "✅ $cmd is available"
    else
        echo "❌ $cmd is NOT available"
    fi
done

echo ""
echo "=========================================="
echo "All tests completed!"
echo "=========================================="
