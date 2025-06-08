#!/bin/bash
# Script to force VS Code to use .venv Python interpreter

VENV_PYTHON="$(pwd)/.venv/bin/python"
SETTINGS_FILE="$(pwd)/.vscode/settings.json"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Error: .venv Python not found at $VENV_PYTHON"
    exit 1
fi

echo "🔧 Setting VS Code Python interpreter to: $VENV_PYTHON"

# Update VS Code settings
mkdir -p "$(pwd)/.vscode"
cat > "$SETTINGS_FILE" << EOL
{
    "python.defaultInterpreterPath": "$VENV_PYTHON",
    "python.pythonPath": "$VENV_PYTHON",
    "terminal.integrated.env.linux": {
        "PATH": "$(pwd)/.venv/bin:\${env:PATH}",
        "VIRTUAL_ENV": "$(pwd)/.venv"
    }
}
EOL

echo "✅ VS Code settings updated. Please reload VS Code window (Ctrl+Shift+P > 'Developer: Reload Window')"
echo "✅ Or run: code --reuse-window ."
