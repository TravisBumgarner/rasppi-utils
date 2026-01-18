#!/bin/bash
#
# Bootstrap script for rasppi-utils
# One-time setup for a Raspberry Pi - installs dependencies and clones the repo
#
# Usage: sudo ./bootstrap.sh
#
# This script is idempotent - safe to run multiple times.

set -e

# Configuration
INSTALL_DIR="/opt/rasppi-utils"
CONFIG_DIR="/etc/rasppi-utils"
REPO_URL="git@github.com:travisbumgarner/rasppi-utils.git"

# Get the actual user (not root) who ran sudo
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo "~${ACTUAL_USER}")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    apt-get update
    apt-get install -y python3 python3-pip python3-venv git
    log_info "System dependencies installed"
}

# Check for SSH key and offer to generate if missing
setup_ssh_key() {
    log_info "Checking SSH key for GitHub access..."

    local ssh_key="${ACTUAL_HOME}/.ssh/id_ed25519"
    local ssh_pub="${ssh_key}.pub"

    if [[ -f "${ssh_pub}" ]]; then
        log_info "SSH key already exists at ${ssh_pub}"
    else
        log_warn "No SSH key found at ${ssh_pub}"
        echo ""
        read -p "Would you like to generate an SSH key for GitHub? (Y/n): " generate_key

        if [[ ! "${generate_key}" =~ ^[Nn]$ ]]; then
            log_info "Generating SSH key..."

            # Create .ssh directory if it doesn't exist
            sudo -u "${ACTUAL_USER}" mkdir -p "${ACTUAL_HOME}/.ssh"
            chmod 700 "${ACTUAL_HOME}/.ssh"

            # Generate the key as the actual user
            sudo -u "${ACTUAL_USER}" ssh-keygen -t ed25519 -C "raspberrypi" -f "${ssh_key}" -N ""

            log_info "SSH key generated"
        else
            log_warn "Skipping SSH key generation"
            log_warn "You will need an SSH key to clone the private repo"
        fi
    fi

    # Display the public key if it exists
    if [[ -f "${ssh_pub}" ]]; then
        echo ""
        echo "=========================================="
        echo "  Your SSH Public Key"
        echo "=========================================="
        echo ""
        cat "${ssh_pub}"
        echo ""
        echo "=========================================="
        echo ""
        echo "Add this key to GitHub:"
        echo "1. Go to https://github.com/settings/keys"
        echo "2. Click 'New SSH key'"
        echo "3. Paste the key above and save"
        echo ""
        read -p "Press Enter once you've added the key to GitHub..."

        # Test GitHub connection
        log_info "Testing GitHub SSH connection..."
        if sudo -u "${ACTUAL_USER}" ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
            log_info "GitHub SSH connection successful"
        else
            log_warn "Could not verify GitHub connection (this may be normal for first-time setup)"
        fi
    fi
}

# Clone or update the repository
clone_or_update_repo() {
    log_info "Setting up repository at ${INSTALL_DIR}..."

    if [[ -d "${INSTALL_DIR}/.git" ]]; then
        # Repository already exists, pull latest changes
        log_info "Repository exists, pulling latest changes..."
        cd "${INSTALL_DIR}"
        git pull
        log_info "Repository updated"
    else
        # Clone the repository
        log_info "Cloning repository..."

        # Remove directory if it exists but isn't a git repo
        if [[ -d "${INSTALL_DIR}" ]]; then
            log_warn "Removing existing non-git directory at ${INSTALL_DIR}"
            rm -rf "${INSTALL_DIR}"
        fi

        # Clone as the actual user to use their SSH key, then fix ownership
        sudo -u "${ACTUAL_USER}" git clone "${REPO_URL}" "${INSTALL_DIR}"

        log_info "Repository cloned"
    fi

    # Ensure proper ownership
    chown -R root:root "${INSTALL_DIR}"
}

# Create virtual environment and install Python dependencies
setup_venv() {
    log_info "Setting up Python virtual environment..."

    # Create venv if it doesn't exist
    if [[ ! -d "${INSTALL_DIR}/.venv" ]]; then
        python3 -m venv "${INSTALL_DIR}/.venv"
        log_info "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi

    # Install/upgrade dependencies
    "${INSTALL_DIR}/.venv/bin/pip" install --upgrade pip
    "${INSTALL_DIR}/.venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

    log_info "Python dependencies installed"
}

# Create config directory
setup_config_dir() {
    log_info "Setting up configuration directory..."

    mkdir -p "${CONFIG_DIR}"
    chmod 755 "${CONFIG_DIR}"

    log_info "Configuration directory created at ${CONFIG_DIR}"
}

# Run sync.sh to configure utilities
run_sync() {
    log_info "Running sync.sh to configure utilities..."

    if [[ -x "${INSTALL_DIR}/sync.sh" ]]; then
        "${INSTALL_DIR}/sync.sh"
    else
        log_warn "sync.sh not found or not executable"
        log_warn "Run 'sudo ${INSTALL_DIR}/sync.sh' manually after it's created"
    fi
}

# Main function
main() {
    echo ""
    echo "=========================================="
    echo "  rasppi-utils Bootstrap Script"
    echo "=========================================="
    echo ""

    check_root
    install_system_deps
    setup_ssh_key
    clone_or_update_repo
    setup_venv
    setup_config_dir
    run_sync

    echo ""
    echo "=========================================="
    log_info "Bootstrap complete!"
    echo "=========================================="
    echo ""
    echo "To manage utilities:"
    echo "  - Edit ${INSTALL_DIR}/utilities.conf to enable/disable utilities"
    echo "  - Run 'sudo ${INSTALL_DIR}/sync.sh' to apply changes"
    echo ""
    echo "To update the installation:"
    echo "  - Run 'sudo ${INSTALL_DIR}/bootstrap.sh' again"
    echo ""
}

main "$@"
