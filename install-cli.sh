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

echo ""
echo "Installation complete!"
echo "Run 'ulmemory --help' to get started"
