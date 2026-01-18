#!/bin/bash
#
# Bootstrap script for rasppi-utils
# Sets up dependencies and virtual environment for the cloned repo
#
# Usage: sudo ./bootstrap.sh
#
# This script is idempotent - safe to run multiple times.

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="/etc/rasppi-utils"

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
    apt-get install -y python3 python3-pip python3-venv
    log_info "System dependencies installed"
}

# Create virtual environment and install Python dependencies
setup_venv() {
    log_info "Setting up Python virtual environment..."

    # Create venv if it doesn't exist
    if [[ ! -d "${SCRIPT_DIR}/.venv" ]]; then
        python3 -m venv "${SCRIPT_DIR}/.venv"
        log_info "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi

    # Install/upgrade dependencies
    "${SCRIPT_DIR}/.venv/bin/pip" install --upgrade pip
    "${SCRIPT_DIR}/.venv/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt"

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

    if [[ -x "${SCRIPT_DIR}/sync.sh" ]]; then
        "${SCRIPT_DIR}/sync.sh"
    else
        log_warn "sync.sh not found or not executable"
        log_warn "Run 'sudo ${SCRIPT_DIR}/sync.sh' manually after it's created"
    fi
}

# Main function
main() {
    echo ""
    echo "=========================================="
    echo "  rasppi-utils Bootstrap Script"
    echo "=========================================="
    echo ""
    log_info "Installing from: ${SCRIPT_DIR}"
    echo ""

    check_root
    install_system_deps
    setup_venv
    setup_config_dir
    run_sync

    echo ""
    echo "=========================================="
    log_info "Bootstrap complete!"
    echo "=========================================="
    echo ""
    echo "To manage utilities:"
    echo "  - Edit ${SCRIPT_DIR}/utilities.conf to enable/disable utilities"
    echo "  - Run 'sudo ${SCRIPT_DIR}/sync.sh' to apply changes"
    echo ""
    echo "To update:"
    echo "  - cd ${SCRIPT_DIR} && git pull && sudo ./bootstrap.sh"
    echo ""
}

main "$@"
