#!/usr/bin/env bash
#
# One-time Cloudflare named-tunnel setup for social-poster.
#
# Instagram's Graph API fetches uploaded photos from a public URL, so this app
# must be reachable from the internet. This creates a named Cloudflare Tunnel,
# auto-creates its DNS record, and points it at the local Flask server — no open
# ports. Run it ON the Pi:
#
#   ssh motioncam@motioncam.local
#   ~/rasppi-utils/social-poster/setup-cloudflare.sh
#
# You'll be asked once to open a URL in a browser and authorize the domain.
# Idempotent — safe to re-run.
#
set -euo pipefail

TUNNEL_NAME="${TUNNEL_NAME:-social-poster}"
HOSTNAME_FQDN="${HOSTNAME_FQDN:-poster.travisbumgarner.photography}"
LOCAL_URL="${LOCAL_URL:-http://localhost:5050}"
CF_DIR="/etc/cloudflared"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is not installed. Run ./deploy.sh (or bootstrap-pi.sh) first." >&2
  exit 1
fi

# 1. Authorize this machine against your Cloudflare account + domain. Creates
#    ~/.cloudflared/cert.pem. Opens (or prints) a URL to approve in a browser.
if [ ! -f "$HOME/.cloudflared/cert.pem" ]; then
  echo "==> Authorize the domain in a browser when the URL appears below."
  echo "    (Pick the zone for ${HOSTNAME_FQDN#*.})"
  cloudflared tunnel login
fi

# 2. Create the named tunnel if it doesn't already exist.
if cloudflared tunnel list --output json | grep -q "\"name\":\"${TUNNEL_NAME}\""; then
  echo "==> Tunnel '${TUNNEL_NAME}' already exists."
else
  echo "==> Creating tunnel '${TUNNEL_NAME}'..."
  cloudflared tunnel create "$TUNNEL_NAME"
fi

# 3. Resolve its UUID + credentials file.
UUID="$(cloudflared tunnel list --output json \
  | python3 -c "import sys,json; print(next(t['id'] for t in json.load(sys.stdin) if t['name']=='${TUNNEL_NAME}'))")"
CRED_SRC="$HOME/.cloudflared/${UUID}.json"
if [ ! -f "$CRED_SRC" ]; then
  echo "Could not find credentials file ${CRED_SRC}" >&2
  exit 1
fi

# 4. Create the public DNS record (CNAME -> the tunnel). This is what was
#    missing before (NXDOMAIN). Safe to re-run.
echo "==> Routing ${HOSTNAME_FQDN} -> tunnel ${TUNNEL_NAME}..."
cloudflared tunnel route dns "$TUNNEL_NAME" "$HOSTNAME_FQDN" || true

# 5. Install config + credentials where the (root-run) service can read them.
echo "==> Writing ${CF_DIR}/config.yml..."
sudo mkdir -p "$CF_DIR"
sudo cp "$CRED_SRC" "$CF_DIR/${UUID}.json"
sudo chmod 600 "$CF_DIR/${UUID}.json"
sudo tee "$CF_DIR/config.yml" >/dev/null <<YML
tunnel: ${UUID}
credentials-file: ${CF_DIR}/${UUID}.json
ingress:
  - hostname: ${HOSTNAME_FQDN}
    service: ${LOCAL_URL}
  - service: http_status:404
YML

# 6. Restart the tunnel service and report.
sudo systemctl restart social-poster-tunnel
sleep 4
echo
echo "tunnel service: $(systemctl is-active social-poster-tunnel)"
echo "==> Done. Verify from anywhere:"
echo "    curl -I https://${HOSTNAME_FQDN}/"
echo "    (DNS may take a minute to propagate the first time.)"
