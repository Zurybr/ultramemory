#!/bin/bash
set -e

echo "Installing Ultramemory CLI..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3.11+ is required"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher is required"
    exit 1
fi

# Create config directory
CONFIG_DIR="$HOME/.ulmemory"
mkdir -p "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/agents"
mkdir -p "$CONFIG_DIR/logs"

echo "Config directory: $CONFIG_DIR"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Creating virtual environment..."
    VENV_DIR="$CONFIG_DIR/venv"
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    echo "Virtual environment created at $VENV_DIR"
else
    echo "Using existing virtual environment: $VIRTUAL_ENV"
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install package in editable mode
echo "Installing ultramemory package..."
pip install -e .

# Create default settings if not exists
if [ ! -f "$CONFIG_DIR/settings.json" ]; then
    cat > "$CONFIG_DIR/settings.json" << 'EOF'
{
  "mode": "local",
  "services": {
    "api": "http://localhost:8000",
    "graphiti": "http://localhost:8001",
    "qdrant": "http://localhost:6333",
    "redis": "localhost:6379",
    "falkordb": "localhost:6370",
    "postgres": "localhost:5432",
    "grafana": "http://localhost:3000",
    "prometheus": "http://localhost:9090"
  },
  "credentials": {
    "postgres": {"user": "postgres", "pass": "postgres"},
    "grafana": {"user": "admin", "pass": "admin"},
    "qdrant": {"api_key": ""},
    "redis": {"password": ""}
  },
  "llm_provider": "openai",
  "embedding_provider": "openai",
  "researcher_topics": [],
  "researcher_schedule": "daily",
  "researcher_output_dir": "./researches"
}
EOF
    echo "Default settings created at $CONFIG_DIR/settings.json"
fi

# Create wrapper script for easy access
echo "Creating wrapper script..."
WRAPPER_FILE="$HOME/.local/bin/ulmemory"
mkdir -p "$HOME/.local/bin"

cat > "$WRAPPER_FILE" << EOF
#!/bin/bash
# Ultramemory CLI wrapper - activates venv and runs command
source "$CONFIG_DIR/venv/bin/activate"
ulmemory "\$@"
EOF

chmod +x "$WRAPPER_FILE"

# Add to PATH if not already there
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "Adding ~/.local/bin to PATH..."

    # Detect shell and add to appropriate rc file
    if [ -n "$ZSH_VERSION" ] || [ "$(basename "$SHELL")" = "zsh" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
        SHELL_RC=".zshrc"
    elif [ -n "$BASH_VERSION" ] || [ "$(basename "$SHELL")" = "bash" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        SHELL_RC=".bashrc"
    else
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.profile"
        SHELL_RC=".profile"
    fi

    echo "Added PATH to ~/$SHELL_RC"
    echo "Run: source ~/$SHELL_RC"
fi

echo ""
echo "Installation complete!"
echo ""
echo "To use ultramemory:"
echo "  1. Run: source ~/$SHELL_RC (or restart your terminal)"
echo "  2. Run: ulmemory --help"
echo ""
echo "Or use directly:"
echo "  ~/.local/bin/ulmemory --help"
