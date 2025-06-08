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

# ============================================================================
# INSTALLATION PHASE: Install tools if they don't exist
# ============================================================================

# Check and install pyenv if needed
PYENV_INSTALLED=false
if [ ! -d "$HOME/.pyenv" ]; then
    echo "📦 Installing pyenv..."
    curl https://pyenv.run | bash
    PYENV_INSTALLED=true
    echo "✅ pyenv installed successfully"
else
    echo "✓ pyenv already installed"
fi

# Check and install Poetry if needed
POETRY_INSTALLED=false
if [ ! -f "$HOME/.local/bin/poetry" ] && ! command -v poetry >/dev/null 2>&1; then
    echo "📦 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    POETRY_INSTALLED=true
    echo "✅ Poetry installed successfully"
else
    echo "✓ Poetry already installed"
fi

# ============================================================================
# ENVIRONMENT SETUP PHASE: Configure environment and PATH
# ============================================================================

# Setup pyenv environment
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

# Initialize pyenv in current shell
if command -v pyenv >/dev/null 2>&1; then
    echo "✓ pyenv is available in current shell"
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
else
    echo "🔧 Initializing pyenv in current shell..."
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
fi

# Setup Poetry environment
export PATH="$HOME/.local/bin:$PATH"

# Verify Poetry is accessible
if command -v poetry >/dev/null 2>&1; then
    echo "✓ Poetry is available in current shell"
else
    echo "🔧 Making Poetry available in current shell..."
    export PATH="$HOME/.local/bin:$PATH"
fi

# ============================================================================
# SHELL PROFILE CONFIGURATION: Set up global availability
# ============================================================================

# Add pyenv to shell profile for global availability
add_to_shell_profile() {
    local profile_file="$1"
    local content="$2"
    
    if [ -f "$profile_file" ]; then
        if ! grep -q "PYENV_ROOT" "$profile_file"; then
            echo "🔧 Adding pyenv configuration to $profile_file..."
            echo "" >> "$profile_file"
            echo "# pyenv configuration" >> "$profile_file"
            echo "$content" >> "$profile_file"
        else
            echo "✓ pyenv configuration already in $profile_file"
        fi
    fi
}

# Configure pyenv in shell profiles
PYENV_CONFIG='export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"'

# Add to common shell profiles
add_to_shell_profile "$HOME/.bashrc" "$PYENV_CONFIG"
add_to_shell_profile "$HOME/.zshrc" "$PYENV_CONFIG"
add_to_shell_profile "$HOME/.profile" "$PYENV_CONFIG"

# Add Poetry to shell profile for global availability
add_poetry_to_shell_profile() {
    local profile_file="$1"
    
    if [ -f "$profile_file" ]; then
        if ! grep -q "\.local/bin" "$profile_file"; then
            echo "🔧 Adding Poetry PATH to $profile_file..."
            echo "" >> "$profile_file"
            echo "# Poetry configuration" >> "$profile_file"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$profile_file"
        else
            echo "✓ Poetry PATH already in $profile_file"
        fi
    fi
}

# Add Poetry to common shell profiles
add_poetry_to_shell_profile "$HOME/.bashrc"
add_poetry_to_shell_profile "$HOME/.zshrc"
add_poetry_to_shell_profile "$HOME/.profile"

# ============================================================================
# PYTHON VERSION AND VIRTUAL ENVIRONMENT SETUP
# ============================================================================

# Check and install Python version if needed
if ! pyenv versions --bare | grep -q "^$PYTHON_VERSION$"; then
    echo "📦 Installing Python $PYTHON_VERSION using pyenv..."
    pyenv install $PYTHON_VERSION
    echo "✅ Python $PYTHON_VERSION installed successfully"
else
    echo "✓ Python $PYTHON_VERSION already installed"
fi

# Set local Python version
if [ "$(pyenv local 2>/dev/null)" != "$PYTHON_VERSION" ]; then
    echo "🔧 Setting local Python version to $PYTHON_VERSION..."
    pyenv local $PYTHON_VERSION
else
    echo "✓ Local Python version already set to $PYTHON_VERSION"
fi

# Check and create virtual environment if needed
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment in .venv..."
    python3 -m venv .venv
    echo "✅ Virtual environment created successfully"
else
    echo "✓ Virtual environment .venv already exists"
fi

# Activate virtual environment for current script session
echo "🔧 Activating virtual environment..."
. .venv/bin/activate
echo "✅ Virtual environment activated"
echo "• Current Python: $(which python)"
echo "• Python version: $(python --version)"

# ============================================================================
# POETRY CONFIGURATION
# ============================================================================
# Configure Poetry settings
echo "🔧 Configuring Poetry..."
if [ "$(poetry config virtualenvs.in-project --local 2>/dev/null)" != "true" ]; then
    echo "🔧 Setting Poetry virtualenvs.in-project to true..."
    poetry config virtualenvs.in-project true
else
    echo "✓ Poetry virtualenvs.in-project already set to true"
fi

if [ -d ".venv" ]; then
    current_env=$(poetry env info --path 2>/dev/null || echo "")
    expected_env="$(pwd)/.venv"
    if [ "$current_env" != "$expected_env" ]; then
        echo "🔧 Setting Poetry to use local .venv..."
        poetry env use .venv/bin/python
        echo "✅ Poetry configured to use local .venv"
    else
        echo "✓ Poetry already using local .venv"
    fi
    
    # Verify Poetry is using the correct environment
    echo "• Poetry environment: $(poetry env info --path 2>/dev/null || echo 'Not configured')"
fi

# ============================================================================
# DEPENDENCY INSTALLATION
# ============================================================================

# Install dependencies if pyproject.toml exists
if [ -f "pyproject.toml" ]; then
    if [ ! -f "poetry.lock" ] || [ "pyproject.toml" -nt "poetry.lock" ]; then
        echo "📦 Installing/updating dependencies with Poetry..."
        poetry install
        echo "✅ Dependencies installed successfully"
    else
        echo "✓ Dependencies already up to date"
    fi
else
    echo "ℹ️ No pyproject.toml found, skipping dependency installation"
fi

# ============================================================================
# VS CODE CONFIGURATION
# ============================================================================

# Configure VS Code workspace settings
configure_vscode_workspace() {
    local vscode_dir=".vscode"
    local settings_file="$vscode_dir/settings.json"
    local python_path="$(pwd)/.venv/bin/python"
    
    # Create .vscode directory if it doesn't exist
    mkdir -p "$vscode_dir"
    
    # Ensure .venv Python exists before configuring
    if [ ! -f "$python_path" ]; then
        echo "❌ Error: Virtual environment Python not found at $python_path"
        exit 1
    fi
    
    # Create or update settings.json with explicit venv priority
    echo "🔧 Creating VS Code workspace settings with .venv priority..."
    cat > "$settings_file" << EOF
{
    "python.defaultInterpreterPath": "$python_path",
    "python.pythonPath": "$python_path",
    "python.terminal.activateEnvironment": true,
    "python.terminal.activateEnvInCurrentTerminal": true,
    "python.venvPath": "$(pwd)",
    "python.venvFolders": [".venv"],
    "python.envFile": "\${workspaceFolder}/.env",
    "python.condaPath": "",
    "python.pipenvPath": "",
    "python.poetryPath": "",
    "python.interpreter.infoVisibility": "always",
    "python.defaultInterpreterPath": "$python_path",
    "terminal.integrated.env.linux": {
        "PATH": "$(pwd)/.venv/bin:\${env:PATH}",
        "VIRTUAL_ENV": "$(pwd)/.venv",
        "VIRTUAL_ENV_PROMPT": "(.venv) "
    },
    "terminal.integrated.profiles.linux": {
        "bash (venv)": {
            "path": "/bin/bash",
            "args": ["--rcfile", "$(pwd)/.vscode/terminal_init.sh"]
        },
        "Python venv": {
            "path": "$python_path",
            "args": []
        }
    },
    "terminal.integrated.defaultProfile.linux": "bash (venv)",
    "python.linting.enabled": true,
    "python.formatting.provider": "black",
    "python.analysis.autoImportCompletions": true,
    "python.analysis.autoSearchPaths": true,
    "python.analysis.extraPaths": [
        "\${workspaceFolder}"
    ],
    "python.analysis.stubPath": "\${workspaceFolder}/.venv/lib/python*/site-packages",
    "files.associations": {
        "*.py": "python"
    },
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "."
    ]
}
EOF
    echo "✅ VS Code workspace settings created with .venv priority"
    
    # Create terminal initialization script
    local terminal_init="$vscode_dir/terminal_init.sh"
    echo "🔧 Creating terminal initialization script..."
    cat > "$terminal_init" << EOF
#!/bin/bash
# VS Code terminal initialization with .venv activation

# Source default bashrc if it exists
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Activate virtual environment
if [ -f "$(pwd)/.venv/bin/activate" ]; then
    source "$(pwd)/.venv/bin/activate"
    export PS1="(.venv) \$PS1"
    echo "🔧 Virtual environment activated: $(pwd)/.venv"
else
    echo "❌ Virtual environment not found at $(pwd)/.venv"
fi

# Ensure .venv/bin is first in PATH
export PATH="$(pwd)/.venv/bin:\$PATH"
export VIRTUAL_ENV="$(pwd)/.venv"
export VIRTUAL_ENV_PROMPT="(.venv) "
EOF
    chmod +x "$terminal_init"
    echo "✅ Terminal initialization script created"
    
    # Create launch.json for debugging with correct Python path
    local launch_file="$vscode_dir/launch.json"
    echo "🔧 Creating VS Code launch configuration..."
    cat > "$launch_file" << EOF
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "\${file}",
            "console": "integratedTerminal",
            "python": "$python_path",
            "env": {
                "PYTHONPATH": "\${workspaceFolder}",
                "PATH": "$(pwd)/.venv/bin:\${env:PATH}",
                "VIRTUAL_ENV": "$(pwd)/.venv"
            },
            "cwd": "\${workspaceFolder}"
        }
    ]
}
EOF
    echo "✅ VS Code launch configuration created"
}

echo "🔧 Configuring VS Code workspace..."
configure_vscode_workspace

# Create VS Code global shell integration for terminals
create_vscode_shell_config() {
    local vscode_config_dir="$HOME/.vscode"
    local vscode_shell_config="$vscode_config_dir/shell_integration.sh"
    
    # Create .vscode directory if it doesn't exist
    mkdir -p "$vscode_config_dir"
    
    # Create VS Code shell integration script with .venv priority
    cat > "$vscode_shell_config" << 'EOF'
#!/bin/bash
# VS Code Shell Integration - .venv priority over pyenv

# Function to find and activate project virtual environment
activate_project_venv() {
    local current_dir="$PWD"
    
    # Look for .venv in current directory and parent directories
    while [ "$current_dir" != "/" ]; do
        if [ -f "$current_dir/.venv/bin/activate" ]; then
            if [ -z "$VIRTUAL_ENV" ] || [ "$VIRTUAL_ENV" != "$current_dir/.venv" ]; then
                # Deactivate current venv if active
                if [ -n "$VIRTUAL_ENV" ]; then
                    deactivate 2>/dev/null || true
                fi
                echo "🔧 Activating .venv: $current_dir/.venv"
                source "$current_dir/.venv/bin/activate"
                
                # Ensure .venv/bin is first in PATH
                export PATH="$current_dir/.venv/bin:${PATH}"
                
                # Override which python to always show venv path
                alias which='function _which() { 
                    if [ "$1" = "python" ] || [ "$1" = "python3" ]; then 
                        echo "$VIRTUAL_ENV/bin/python"; 
                    else 
                        command which "$@"; 
                    fi; 
                }; _which'
                
                return 0
            else
                # Already in correct venv, ensure PATH priority
                export PATH="$VIRTUAL_ENV/bin:${PATH#*:}"
                return 0
            fi
        fi
        current_dir="$(dirname "$current_dir")"
    done
    
    # No .venv found, set up pyenv as fallback
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    if command -v pyenv >/dev/null 2>&1; then
        eval "$(pyenv init --path)"
        eval "$(pyenv init -)"
    fi
    
    # Poetry configuration as fallback
    export PATH="$HOME/.local/bin:$PATH"
    
    # If any venv was active, deactivate it
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "🔧 Deactivating virtual environment (no .venv found in project)"
        deactivate 2>/dev/null || true
        unalias which 2>/dev/null || true
    fi
}

# Override cd to auto-activate virtual environments
cd() {
    builtin cd "$@"
    activate_project_venv
}

# Override code command to ensure .venv is used
code() {
    local current_dir="$PWD"
    
    # Find .venv in current or parent directories
    while [ "$current_dir" != "/" ]; do
        if [ -f "$current_dir/.venv/bin/python" ]; then
            echo "🔧 Opening VS Code with .venv Python: $current_dir/.venv/bin/python"
            break
        fi
        current_dir="$(dirname "$current_dir")"
    done
    
    command code "$@"
}

# Activate venv for current directory on script load
activate_project_venv
EOF
    
    chmod +x "$vscode_shell_config"
    echo "✅ Created VS Code shell integration with .venv priority"
}

# Create a script to force VS Code to use .venv Python
create_vscode_python_script() {
    local script_path="$(pwd)/set_vscode_python.sh"
    
    cat > "$script_path" << EOF
#!/bin/bash
# Script to force VS Code to use .venv Python interpreter

VENV_PYTHON="\$(pwd)/.venv/bin/python"
SETTINGS_FILE="\$(pwd)/.vscode/settings.json"

if [ ! -f "\$VENV_PYTHON" ]; then
    echo "❌ Error: .venv Python not found at \$VENV_PYTHON"
    exit 1
fi

echo "🔧 Setting VS Code Python interpreter to: \$VENV_PYTHON"

# Update VS Code settings
mkdir -p "\$(pwd)/.vscode"
cat > "\$SETTINGS_FILE" << EOL
{
    "python.defaultInterpreterPath": "\$VENV_PYTHON",
    "python.pythonPath": "\$VENV_PYTHON",
    "terminal.integrated.env.linux": {
        "PATH": "\$(pwd)/.venv/bin:\\\${env:PATH}",
        "VIRTUAL_ENV": "\$(pwd)/.venv"
    }
}
EOL

echo "✅ VS Code settings updated. Please reload VS Code window (Ctrl+Shift+P > 'Developer: Reload Window')"
echo "✅ Or run: code --reuse-window ."
EOF
    
    chmod +x "$script_path"
    echo "✅ Created VS Code Python override script: $script_path"
}

echo "🔧 Creating VS Code Python override script..."
create_vscode_python_script

# ============================================================================
# ENVIRONMENT REFRESH AND COMPLETION
# ============================================================================

# Force reload the current shell environment for immediate use
echo "🔄 Refreshing shell environment..."
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
if command -v pyenv >/dev/null 2>&1; then
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
fi
export PATH="$HOME/.local/bin:$PATH"

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "📋 Summary:"
echo "• Python $PYTHON_VERSION (system): $(which python3)"
echo "• Python (virtual env): $(pwd)/.venv/bin/python"
echo "• Virtual environment: $(pwd)/.venv (activated: $([[ -n "$VIRTUAL_ENV" ]] && echo "Yes" || echo "No"))"
echo "• Poetry: $(which poetry 2>/dev/null || echo 'Available after shell reload')"
echo "• VS Code workspace configured with .venv priority"
echo ""
echo "🔧 VS Code Configuration:"
echo "• Python interpreter: $(pwd)/.venv/bin/python (PRIORITY OVER PYENV)"
echo "• Terminal profile: 'bash (venv)' with .venv activation"
echo "• Launch configuration: Uses .venv Python for debugging"
echo ""
echo "🎯 To ensure VS Code uses .venv:"
echo "   1. Open VS Code: code ."
echo "   2. Press Ctrl+Shift+P"
echo "   3. Type 'Python: Select Interpreter'"
echo "   4. Choose: $(pwd)/.venv/bin/python"
echo "   5. Reload window: Ctrl+Shift+P > 'Developer: Reload Window'"
echo ""
echo "🔄 If 'which python' still shows pyenv, run:"
echo "   ./set_vscode_python.sh"
echo "   source .venv/bin/activate"
echo ""
echo "📝 Manual verification:"
echo "   source .venv/bin/activate"
echo "   which python  # Should show: $(pwd)/.venv/bin/python"
