#!/bin/bash
#
# Bootstrap script for the Raspberry Pi
# Sets the hostname/user, installs dependencies, and configures utilities.
#
# Usage: sudo ./bootstrap-pi.sh
#
# This script is idempotent - safe to run multiple times.

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="/etc/rasppi-utils"
PI_HOSTNAME="rasppi-utils"
PI_USER="rasppi-utils"
PI_PASS="rasppi-utils"

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
    apt-get install -y python3 python3-pip python3-venv avahi-daemon openssh-server curl
    log_info "System dependencies installed"
}

# Install cloudflared (Cloudflare Tunnel) — needed by utilities that must be
# reachable from the public internet, e.g. social-poster's Instagram image URLs.
install_cloudflared() {
    if command -v cloudflared >/dev/null 2>&1; then
        log_info "cloudflared already installed ($(cloudflared --version 2>/dev/null | head -1))"
        return
    fi
    log_info "Installing cloudflared..."
    local arch deb
    arch="$(dpkg --print-architecture)"   # arm64, armhf, amd64
    deb="$(mktemp --suffix=.deb)"
    curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${arch}.deb" -o "$deb"
    dpkg -i "$deb" || apt-get install -f -y
    rm -f "$deb"
    log_info "cloudflared installed ($(cloudflared --version 2>/dev/null | head -1))"
}

# Set hostname so the Pi is reachable at <hostname>.local via mDNS
setup_hostname() {
    log_info "Setting hostname to ${PI_HOSTNAME}..."
    hostnamectl set-hostname "${PI_HOSTNAME}"
    sed -i "/127.0.1.1/d" /etc/hosts
    printf "127.0.1.1\t%s\n" "${PI_HOSTNAME}" >> /etc/hosts
    systemctl enable --now avahi-daemon ssh
    log_info "Pi reachable at ${PI_HOSTNAME}.local"
}

# Create the rasppi-utils login user with a known password
setup_user() {
    if ! id "${PI_USER}" &>/dev/null; then
        log_info "Creating user ${PI_USER}..."
        useradd -m -s /bin/bash "${PI_USER}"
        usermod -aG sudo "${PI_USER}"
    fi
    echo "${PI_USER}:${PI_PASS}" | chpasswd
    log_info "User '${PI_USER}' ready (password: ${PI_PASS})"
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
    install_cloudflared
    setup_hostname
    setup_user
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
    echo "  - cd ${SCRIPT_DIR} && git pull && sudo ./bootstrap-pi.sh"
    echo ""
}

main "$@"
