#!/bin/bash

set -e

echo "🚀 Setting up Python development environment..."

# Ensure required tools are present
if [ ! -x "$(command -v curl)" ]; then
    echo "❌ Error: curl is not in PATH or not executable."
    which curl || echo "No curl found in PATH."
    exit 1
else
    echo "✓ curl is available"
fi

if [ ! -x "$(command -v python3)" ]; then
    echo "❌ Error: python3 is not in PATH or not executable."
    which python3 || echo "No python3 found in PATH."
    exit 1
else
    echo "✓ python3 is available"
fi

# Read Python version from .python-version file
if [ -f ".python-version" ]; then
    PYTHON_VERSION=$(cat .python-version | tr -d '\n\r')
    echo "Using Python version $PYTHON_VERSION from .python-version file"
else
    echo "❌ Error: .python-version file not found"
    exit 1
fi

# Check and install pyenv if needed
if [ ! -d "$HOME/.pyenv" ]; then
    echo "Installing pyenv..."
    curl https://pyenv.run | bash
else
    echo "✓ pyenv already installed"
fi

# Update shell for pyenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

# Only initialize pyenv if pyenv was just installed or not in current shell
if command -v pyenv >/dev/null 2>&1; then
    echo "✓ pyenv is already available in current shell"
else
    echo "Initializing pyenv in current shell..."
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
fi

# Check and install Python version if needed
if ! pyenv versions --bare | grep -q "^$PYTHON_VERSION$"; then
    echo "Installing Python $PYTHON_VERSION using pyenv..."
    pyenv install $PYTHON_VERSION
else
    echo "✓ Python $PYTHON_VERSION already installed"
fi

# Set local Python version
if [ "$(pyenv local 2>/dev/null)" != "$PYTHON_VERSION" ]; then
    echo "Setting local Python version to $PYTHON_VERSION..."
    pyenv local $PYTHON_VERSION
else
    echo "✓ Local Python version already set to $PYTHON_VERSION"
fi

# Check and create virtual environment if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in .venv..."
    python3 -m venv .venv
else
    echo "✓ Virtual environment .venv already exists"
fi

# Check and install Poetry if needed
if ! command -v poetry >/dev/null 2>&1; then
    echo "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "✓ Poetry already installed"
    export PATH="$HOME/.local/bin:$PATH"
fi

# Configure Poetry
echo "Configuring Poetry..."
if [ "$(poetry config virtualenvs.in-project --local 2>/dev/null)" != "true" ]; then
    echo "Setting Poetry virtualenvs.in-project to true..."
    poetry config virtualenvs.in-project true
else
    echo "✓ Poetry virtualenvs.in-project already set to true"
fi

if [ -d ".venv" ]; then
    current_env=$(poetry env info --path 2>/dev/null || echo "")
    expected_env="$(pwd)/.venv"
    if [ "$current_env" != "$expected_env" ]; then
        echo "Setting Poetry to use local .venv..."
        poetry env use .venv/bin/python
    else
        echo "✓ Poetry already using local .venv"
    fi
fi

# Install dependencies if pyproject.toml exists
if [ -f "pyproject.toml" ]; then
    if [ ! -f "poetry.lock" ] || [ "pyproject.toml" -nt "poetry.lock" ]; then
        echo "Installing/updating dependencies with Poetry..."
        poetry install
    else
        echo "✓ Dependencies already up to date"
    fi
else
    echo "ℹ️ No pyproject.toml found, skipping dependency installation"
fi

echo "✅ Done: pyenv + venv + poetry environment is set up"
