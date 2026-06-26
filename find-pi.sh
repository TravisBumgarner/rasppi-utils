#!/usr/bin/env bash
# find-pi.sh — locate a Raspberry Pi on the local network
set -euo pipefail

# 1. Try mDNS first (works if the Pi advertises raspberrypi.local)
HOSTNAME="${1:-raspberrypi.local}"
if ip=$(ping -c1 -W1 "$HOSTNAME" 2>/dev/null | sed -n 's/.*(\([0-9.]*\)).*/\1/p' | head -n1) && [ -n "$ip" ]; then
  echo "Found via mDNS: $HOSTNAME -> $ip"
  exit 0
fi

# 2. Fall back to scanning the ARP table for Raspberry Pi MAC prefixes (OUIs)
echo "mDNS lookup failed; scanning ARP table for Raspberry Pi MAC addresses..."

# Populate the ARP cache by pinging the local /24 broadcast (best effort)
subnet=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
if [ -n "${subnet:-}" ]; then
  base="${subnet%.*}"
  for i in $(seq 1 254); do ping -c1 -W1 "$base.$i" >/dev/null 2>&1 & done
  wait
fi

# Raspberry Pi Foundation OUIs
PI_OUIS="b8:27:eb|dc:a6:32|e4:5f:01|28:cd:c1|d8:3a:dd|2c:cf:67"

arp -a | grep -Ei "$PI_OUIS" || {
  echo "No Raspberry Pi found. Make sure it is powered on and connected to the same network."
  exit 1
}
