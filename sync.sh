#!/bin/bash
#
# Sync script for rasppi-utils
# Manages which utilities are enabled/disabled based on utilities.conf
#
# Usage: sudo ./sync.sh [--status]
#
# This script is idempotent - safe to run multiple times.

set -e

# Configuration
CONFIG_DIR="/etc/rasppi-utils"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Get all available utilities (directories with systemd/ subdirectory)
get_available_utilities() {
    local utilities=()
    for dir in "${SCRIPT_DIR}"/*/; do
        local name=$(basename "$dir")
        # Skip non-utility directories
        if [[ -d "${dir}systemd" ]]; then
            utilities+=("$name")
        fi
    done
    echo "${utilities[@]}"
}

# Get enabled utilities from utilities.conf
get_enabled_utilities() {
    local conf_file="${SCRIPT_DIR}/utilities.conf"
    local utilities=()

    if [[ ! -f "$conf_file" ]]; then
        log_warn "utilities.conf not found at ${conf_file}"
        return
    fi

    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip comments and empty lines
        line=$(echo "$line" | sed 's/#.*//' | xargs)
        if [[ -n "$line" ]]; then
            utilities+=("$line")
        fi
    done < "$conf_file"

    echo "${utilities[@]}"
}

# Check if a utility is in the enabled list
is_utility_enabled() {
    local utility="$1"
    local enabled
    read -ra enabled <<< "$(get_enabled_utilities)"

    for u in "${enabled[@]}"; do
        if [[ "$u" == "$utility" ]]; then
            return 0
        fi
    done
    return 1
}

# Prompt for utility configuration
prompt_for_config() {
    local utility="$1"
    local config_dir="${CONFIG_DIR}/${utility}"
    local env_file="${config_dir}/.env"
    local example_file="${SCRIPT_DIR}/${utility}/config/.env.example"

    # Create config directory if needed
    mkdir -p "$config_dir"

    # If .env already exists, skip prompting
    if [[ -f "$env_file" ]]; then
        log_info "Configuration exists for ${utility}"
        return 0
    fi

    # Check if example file exists
    if [[ ! -f "$example_file" ]]; then
        log_warn "No .env.example found for ${utility}, skipping configuration"
        return 0
    fi

    echo ""
    echo "=========================================="
    echo "  Configure: ${utility}"
    echo "=========================================="
    echo ""

    # Read the example file and prompt for each variable
    local temp_env=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Preserve comments
        if [[ "$line" =~ ^#.* ]] || [[ -z "$line" ]]; then
            temp_env+="${line}"$'\n'
            continue
        fi

        # Parse VAR=value
        if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            local var_name="${BASH_REMATCH[1]}"
            local default_value="${BASH_REMATCH[2]}"

            echo "Enter value for ${var_name}"
            echo "  (default: ${default_value})"
            read -p "  > " user_value

            if [[ -z "$user_value" ]]; then
                user_value="$default_value"
            fi

            temp_env+="${var_name}=${user_value}"$'\n'
        else
            temp_env+="${line}"$'\n'
        fi
    done < "$example_file"

    # Write the config file
    echo -n "$temp_env" > "$env_file"
    chmod 600 "$env_file"

    log_info "Configuration saved to ${env_file}"
}

# Install systemd units for a utility
install_systemd_units() {
    local utility="$1"
    local systemd_src="${SCRIPT_DIR}/${utility}/systemd"

    if [[ ! -d "$systemd_src" ]]; then
        log_warn "No systemd directory for ${utility}"
        return 0
    fi

    log_info "Installing systemd units for ${utility}..."

    # Install service files (replacing {{INSTALL_DIR}} placeholder with actual path)
    for unit_file in "${systemd_src}"/*.service; do
        if [[ -f "$unit_file" ]]; then
            local unit_name=$(basename "$unit_file")
            sed "s|{{INSTALL_DIR}}|${SCRIPT_DIR}|g" "$unit_file" > "/etc/systemd/system/${unit_name}"
            log_info "  Installed ${unit_name}"
        fi
    done

    # Install timer files
    for unit_file in "${systemd_src}"/*.timer; do
        if [[ -f "$unit_file" ]]; then
            local unit_name=$(basename "$unit_file")
            cp "$unit_file" "/etc/systemd/system/${unit_name}"
            log_info "  Installed ${unit_name}"
        fi
    done
}

# Enable and start a utility's systemd units
enable_utility() {
    local utility="$1"
    local systemd_src="${SCRIPT_DIR}/${utility}/systemd"

    log_info "Enabling ${utility}..."

    # Enable and start timers first (they trigger services)
    for timer_file in "${systemd_src}"/*.timer; do
        if [[ -f "$timer_file" ]]; then
            local timer_name=$(basename "$timer_file")
            systemctl enable "$timer_name" 2>/dev/null || true
            systemctl start "$timer_name" 2>/dev/null || true
            log_info "  Started ${timer_name}"
        fi
    done

    # Enable services (but don't start if they have a timer)
    for service_file in "${systemd_src}"/*.service; do
        if [[ -f "$service_file" ]]; then
            local service_name=$(basename "$service_file")
            local timer_name="${service_name%.service}.timer"

            # Only enable, don't start (timer will trigger it)
            systemctl enable "$service_name" 2>/dev/null || true

            # If no timer exists, start the service
            if [[ ! -f "${systemd_src}/${timer_name}" ]]; then
                systemctl start "$service_name" 2>/dev/null || true
                log_info "  Started ${service_name}"
            else
                log_info "  Enabled ${service_name} (triggered by timer)"
            fi
        fi
    done
}

# Disable and stop a utility's systemd units
disable_utility() {
    local utility="$1"

    log_info "Disabling ${utility}..."

    # Find and disable/stop service units for this utility
    for unit_file in /etc/systemd/system/${utility}*.service; do
        if [[ -f "$unit_file" ]]; then
            local unit_name=$(basename "$unit_file")

            # Stop and disable
            systemctl stop "$unit_name" 2>/dev/null || true
            systemctl disable "$unit_name" 2>/dev/null || true

            # Remove the unit file
            rm -f "$unit_file"

            log_info "  Removed ${unit_name}"
        fi
    done

    # Find and disable/stop timer units for this utility
    for unit_file in /etc/systemd/system/${utility}*.timer; do
        if [[ -f "$unit_file" ]]; then
            local unit_name=$(basename "$unit_file")

            # Stop and disable
            systemctl stop "$unit_name" 2>/dev/null || true
            systemctl disable "$unit_name" 2>/dev/null || true

            # Remove the unit file
            rm -f "$unit_file"

            log_info "  Removed ${unit_name}"
        fi
    done
}

# Show status of all utilities
show_status() {
    echo ""
    echo "=========================================="
    echo "  Utility Status"
    echo "=========================================="
    echo ""

    local available
    read -ra available <<< "$(get_available_utilities)"

    for utility in "${available[@]}"; do
        local status_color="${RED}"
        local status_text="disabled"

        if is_utility_enabled "$utility"; then
            status_color="${GREEN}"
            status_text="enabled"
        fi

        echo -e "  ${BLUE}${utility}${NC}: ${status_color}${status_text}${NC}"

        # Show systemd unit status if enabled
        if is_utility_enabled "$utility"; then
            # Check service units
            for unit_file in /etc/systemd/system/${utility}*.service; do
                if [[ -f "$unit_file" ]]; then
                    local unit_name=$(basename "$unit_file")
                    local active_state=$(systemctl is-active "$unit_name" 2>/dev/null || echo "inactive")
                    local enabled_state=$(systemctl is-enabled "$unit_name" 2>/dev/null || echo "disabled")

                    local active_color="${RED}"
                    if [[ "$active_state" == "active" ]]; then
                        active_color="${GREEN}"
                    fi

                    echo -e "    └─ ${unit_name}: ${active_color}${active_state}${NC} (${enabled_state})"
                fi
            done

            # Check timer units
            for unit_file in /etc/systemd/system/${utility}*.timer; do
                if [[ -f "$unit_file" ]]; then
                    local unit_name=$(basename "$unit_file")
                    local active_state=$(systemctl is-active "$unit_name" 2>/dev/null || echo "inactive")
                    local enabled_state=$(systemctl is-enabled "$unit_name" 2>/dev/null || echo "disabled")

                    local active_color="${RED}"
                    if [[ "$active_state" == "active" ]]; then
                        active_color="${GREEN}"
                    fi

                    echo -e "    └─ ${unit_name}: ${active_color}${active_state}${NC} (${enabled_state})"
                fi
            done
        fi
    done

    echo ""
}

# Sync all utilities based on utilities.conf
sync_utilities() {
    local available
    local enabled

    read -ra available <<< "$(get_available_utilities)"
    read -ra enabled <<< "$(get_enabled_utilities)"

    local changes_made=false

    # Process each available utility
    for utility in "${available[@]}"; do
        if is_utility_enabled "$utility"; then
            # Utility should be enabled
            prompt_for_config "$utility"
            install_systemd_units "$utility"
            enable_utility "$utility"
            changes_made=true
        else
            # Utility should be disabled
            disable_utility "$utility"
            changes_made=true
        fi
    done

    # Reload systemd if changes were made
    if [[ "$changes_made" == true ]]; then
        log_info "Reloading systemd daemon..."
        systemctl daemon-reload
    fi
}

# Main function
main() {
    # Handle --status flag
    if [[ "$1" == "--status" ]]; then
        show_status
        exit 0
    fi

    echo ""
    echo "=========================================="
    echo "  rasppi-utils Sync"
    echo "=========================================="
    echo ""

    check_root
    sync_utilities

    echo ""
    echo "=========================================="
    log_info "Sync complete!"
    echo "=========================================="
    echo ""
    echo "Run 'sudo ${SCRIPT_DIR}/sync.sh --status' to see utility status"
    echo ""
}

main "$@"
