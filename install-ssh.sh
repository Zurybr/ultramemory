#!/bin/bash
#
# Ultramemory CLI SSH Installer for Linux/Mac
# Run with: ./install-ssh.sh
#
# This installer configures the local CLI to execute commands
# on a remote server via SSH
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Ultramemory CLI SSH Installer for Linux      ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================
# Step 1: Gather SSH Configuration
# ============================================

echo -e "${YELLOW}[1/4] Configuring SSH Connection...${NC}"

# Get Server IP
read -p "Enter the server IP address (e.g., 192.168.1.100 or server.example.com): " SERVER_IP

if [ -z "$SERVER_IP" ]; then
    echo -e "${RED}Error: Server IP is required${NC}"
    exit 1
fi

# Get SSH User
read -p "Enter the SSH username (e.g., zurybr): " SSH_USER

if [ -z "$SSH_USER" ]; then
    echo -e "${RED}Error: SSH username is required${NC}"
    exit 1
fi

# Check if SSH key exists
SSH_KEY_PATH="$HOME/.ssh/id_rsa"
if [ -f "$SSH_KEY_PATH" ]; then
    echo -e "SSH Key Status: ${GREEN}Found at $SSH_KEY_PATH${NC}"
    HAS_SSH_KEY=true
else
    echo -e "SSH Key Status: ${YELLOW}Not found${NC}"
    HAS_SSH_KEY=false
fi

# If no SSH key, ask if user wants to generate
if [ "$HAS_SSH_KEY" = false ]; then
    echo ""
    read -p "No SSH key found. Generate and upload to server? (y/n): " GEN_KEY_CHOICE
    if [ "$GEN_KEY_CHOICE" = "y" ] || [ "$GEN_KEY_CHOICE" = "Y" ]; then
        echo ""
        echo -e "${CYAN}Generating SSH key pair...${NC}"
        ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_PATH" -N ""
        HAS_SSH_KEY=true
        UPLOAD_KEY=true
    fi
fi

# Upload SSH key if requested
if [ "$UPLOAD_KEY" = true ] && [ "$HAS_SSH_KEY" = true ]; then
    echo ""
    echo -e "${CYAN}Uploading SSH key to server...${NC}"

    # Check for sshpass
    if command -v sshpass &> /dev/null; then
        read -p "Enter password for $SSH_USER@$SERVER_IP: " -s SSHPASS
        echo ""

        # Copy key to server
        sshpass -p "$SSHPASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$(cat $SSH_KEY_PATH.pub)' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

        echo -e "${GREEN}SSH key uploaded successfully!${NC}"

        # Save password for later use
        USE_SSHPASS=true
        SSHPASS_ENCODED=$(echo -n "$SSHPASS" | base64)
    else
        echo -e "${YELLOW}sshpass not found. Please manually add this key to the server:${NC}"
        echo ""
        cat "$SSH_KEY_PATH.pub"
        echo ""
        echo -e "${YELLOW}Add the above key to ~/.ssh/authorized_keys on the server${NC}"
        echo ""
        read -p "Press Enter when done..."
        USE_SSHPASS=false
    fi
fi

# Test SSH connection
echo ""
echo -e "${CYAN}Testing SSH connection to $SSH_USER@$SERVER_IP...${NC}"

if [ "$USE_SSHPASS" = true ]; then
    SSH_TEST=$(sshpass -p "$SSHPASS" ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "echo 'SSH connection OK'" 2>&1)
else
    SSH_TEST=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "echo 'SSH connection OK'" 2>&1)
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Could not establish SSH connection${NC}"
    echo "$SSH_TEST"
    exit 1
fi

echo -e "${GREEN}SSH connection verified!${NC}"

# ============================================
# Step 2: Verify Ultramemory on server
# ============================================

echo ""
echo -e "${YELLOW}[2/4] Verifying Ultramemory installation on server...${NC}"

if [ "$USE_SSHPASS" = true ]; then
    REMOTE_CHECK=$(sshpass -p "$SSHPASS" ssh -o ConnectTimeout=10 "$SSH_USER@$SERVER_IP" "which ulmemory" 2>&1)
else
    REMOTE_CHECK=$(ssh -o ConnectTimeout=10 "$SSH_USER@$SERVER_IP" "which ulmemory" 2>&1)
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Ultramemory CLI not found on server${NC}"
    echo -e "${YELLOW}Please install Ultramemory on the server first using install-cli.sh${NC}"
    exit 1
fi

echo -e "${GREEN}Ultramemory found on server!${NC}"

# ============================================
# Step 3: Create local configuration
# ============================================

echo ""
echo -e "${YELLOW}[3/4] Creating local SSH configuration...${NC}"

CONFIG_DIR="$HOME/.ulmemory"
mkdir -p "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/agents"
mkdir -p "$CONFIG_DIR/logs"

# Create SSH config file
SSH_CONFIG_FILE="$CONFIG_DIR/ssh_config.json"

# Create JSON config
cat > "$SSH_CONFIG_FILE" << EOF
{
  "server_ip": "$SERVER_IP",
  "ssh_user": "$SSH_USER",
  "use_sshpass": $USE_SSHPASS,
  "sshpass_path": "$(which sshpass 2>/dev/null || echo "")",
  "created_at": "$(date '+%Y-%m-%d %H:%M:%S')"
}
EOF

# Save password if using sshpass (base64 encoded)
if [ "$USE_SSHPASS" = true ]; then
    echo "$SSHPASS_ENCODED" > "$CONFIG_DIR/.sshpass_encoded"
fi

echo -e "SSH config saved to $SSH_CONFIG_FILE"

# ============================================
# Step 4: Create SSH wrapper script
# ============================================

echo ""
echo -e "${YELLOW}[4/4] Creating SSH wrapper script...${NC}"

WRAPPER_FILE="$HOME/.local/bin/ulmemory-ssh"

# Create wrapper script
cat > "$WRAPPER_FILE" << 'WRAPPER_EOF'
#!/bin/bash
#
# Ultramemory CLI SSH Wrapper
# Executes commands on the remote server via SSH
#

# Load SSH config
CONFIG_DIR="$HOME/.ulmemory"
SSH_CONFIG_FILE="$CONFIG_DIR/ssh_config.json"

if [ ! -f "$SSH_CONFIG_FILE" ]; then
    echo "Error: SSH config not found. Run install-ssh.sh first."
    exit 1
fi

# Parse config
SERVER_IP=$(grep -o '"server_ip"[[:space:]]*:[[:space:]]*"[^"]*"' "$SSH_CONFIG_FILE" | sed 's/.*"\([^"]*\)"$/\1/')
SSH_USER=$(grep -o '"ssh_user"[[:space:]]*:[[:space:]]*"[^"]*"' "$SSH_CONFIG_FILE" | sed 's/.*"\([^"]*\)"$/\1/')
USE_SSHPASS=$(grep -o '"use_sshpass"[[:space:]]*:[[:space:]]*[^,}]*' "$SSH_CONFIG_FILE" | sed 's/.*:[[:space:]]*//')
SSHPASS_PATH=$(grep -o '"sshpass_path"[[:space:]]*:[[:space:]]*"[^"]*"' "$SSH_CONFIG_FILE" | sed 's/.*"\([^"]*\)"$/\1/')

# Build remote command
REMOTE_CMD="ulmemory $@"

# Execute via SSH
if [ "$USE_SSHPASS" = "true" ] && [ -f "$CONFIG_DIR/.sshpass_encoded" ]; then
    SSHPASS=$(cat "$CONFIG_DIR/.sshpass_encoded" | base64 -d)
    $SSHPASS_PATH -p "$SSHPASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "${SSH_USER}@${SERVER_IP}" "$REMOTE_CMD"
else
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "${SSH_USER}@${SERVER_IP}" "$REMOTE_CMD"
fi

exit $?
WRAPPER_EOF

chmod +x "$WRAPPER_FILE"

# Create convenience wrapper that replaces 'ulmemory' command
# (Only if user agrees)
echo ""
read -p "Replace 'ulmemory' command to use SSH by default? (y/n): " REPLACE_CMD

if [ "$REPLACE_CMD" = "y" ] || [ "$REPLACE_CMD" = "Y" ]; then
    # Backup existing ulmemory if exists
    if [ -f "$HOME/.local/bin/ulmemory" ]; then
        mv "$HOME/.local/bin/ulmemory" "$HOME/.local/bin/ulmemory-local.bak"
        echo "Backed up existing ulmemory to ulmemory-local.bak"
    fi

    # Create symlink or copy
    ln -sf "$WRAPPER_FILE" "$HOME/.local/bin/ulmemory"
    echo "Created 'ulmemory' command pointing to SSH wrapper"
else
    echo "SSH wrapper installed as 'ulmemory-ssh'"
    echo "Use 'ulmemory-ssh add \"text\"' to run via SSH"
fi

# Add to PATH if needed
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "Adding ~/.local/bin to PATH..."

    SHELL_RC=""
    if [ -n "$ZSH_VERSION" ] || [ "$(basename "$SHELL")" = "zsh" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
        SHELL_RC=".zshrc"
    elif [ -n "$BASH_VERSION" ] || [ "$(basename "$SHELL")" = "bash" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        SHELL_RC=".bashrc"
    fi

    if [ -n "$SHELL_RC" ]; then
        echo "Added PATH to ~/$SHELL_RC"
        echo "Run: source ~/$SHELL_RC"
    fi
fi

# ============================================
# Done
# ============================================

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Installation Complete!                  ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Server: $SSH_USER@$SERVER_IP${NC}"
echo -e "${CYAN}Mode: SSH Remote Execution${NC}"
echo ""
echo -e "${YELLOW}Usage:${NC}"
echo -e "  ulmemory add \"my memory\"       -> SSH to server and add memory"
echo -e "  ulmemory query \"search\"        -> Query on remote server"
echo -e "  ulmemory status                  -> Show remote status"
echo -e "  ulmemory up                      -> Start services on server"
echo -e "  ulmemory memory add \"text\"      -> Add memory"
echo -e "  ulmemory memory query \"term\"   -> Query memory"
echo ""
echo -e "Restart terminal or run: source ~/$SHELL_RC"
echo ""
