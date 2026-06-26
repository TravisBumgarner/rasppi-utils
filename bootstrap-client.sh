#!/usr/bin/env bash
#
# Bootstrap script for your laptop/desktop.
# Connects to the Pi over SSH. Run after bootstrap-pi.sh has set up the Pi.
#
# Usage: ./bootstrap-client.sh [host]   (default host: rasppi-utils.local)

set -euo pipefail

USER="rasppi-utils"
HOST="${1:-rasppi-utils.local}"

if ! ping -c1 -W1 "$HOST" >/dev/null 2>&1; then
  echo "$HOST not responding; scanning the network..."
  "$(dirname "$0")/find-pi.sh" || true
  echo "Re-run with the IP if needed: ./bootstrap-client.sh <ip>"
  exit 1
fi

echo "Connecting to ${USER}@${HOST} (password: rasppi-utils)..."
exec ssh "${USER}@${HOST}"
