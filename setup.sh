#!/bin/bash
# Setup script for Membership Impact Chatbot
# This script creates and activates a virtual environment, then installs dependencies

set -e  # Exit on error

echo "Setting up Membership Impact Chatbot..."

# Check if virtual environment already exists
if [ -d ".venv" ]; then
    echo "Virtual environment already exists."
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf .venv
    else
        echo "Using existing virtual environment."
        source .venv/bin/activate
        echo "Virtual environment activated."
        echo "Installing/updating dependencies..."
        pip install --upgrade pip
        pip install -r requirements.txt
        echo "Setup complete!"
        echo ""
        echo "To activate the virtual environment in the future, run:"
        echo "  source .venv/bin/activate"
        exit 0
    fi
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Virtual environment is now activated."
echo "To activate it in the future, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the app:"
echo "  python app/dashboard.py"
echo "  # Or use: ./run_dashboard.sh"
