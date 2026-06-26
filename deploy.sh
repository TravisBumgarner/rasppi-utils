#!/usr/bin/env bash
#
# Deploy rasppi-utils to a Raspberry Pi over SSH (run from your laptop).
#
# Updates an existing checkout without re-running bootstrap-pi.sh (so it won't
# touch the Pi's hostname/login user). It:
#   1. clones-or-pulls the repo into ~ on the Pi,
#   2. ensures the shared Python venv + deps,
#   3. ensures cloudflared is installed,
#   4. runs `sudo ./sync.sh` (installs/enables systemd units from utilities.conf),
#   5. sets up the social-poster Cloudflare Tunnel token (Instagram), then
#   6. prints service status.
#
# Idempotent — safe to run repeatedly.
#
# Usage:
#   ./deploy.sh                       # defaults to motioncam@motioncam.local
#   ./deploy.sh pi@raspberrypi.local  # custom user@host
#
set -euo pipefail

TARGET="${1:-motioncam@motioncam.local}"
REPO_URL="${REPO_URL:-https://github.com/TravisBumgarner/rasppi-utils.git}"
ENV_FILE="/etc/rasppi-utils/social-poster/.env"

echo "==> Deploying to ${TARGET}"

# --- 1-4: code, deps, cloudflared, sync -------------------------------------
ssh "${TARGET}" REPO_URL="${REPO_URL}" 'bash -s' <<'REMOTE'
set -euo pipefail
cd "$HOME"

echo "==> Repo"
if [ -d rasppi-utils/.git ]; then
  git -C rasppi-utils pull --ff-only
else
  git clone "$REPO_URL" rasppi-utils
fi
cd "$HOME/rasppi-utils"
git log --oneline -1

echo "==> Python venv + deps"
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

echo "==> cloudflared"
if command -v cloudflared >/dev/null 2>&1; then
  echo "    present: $(cloudflared --version | head -1)"
else
  arch="$(dpkg --print-architecture)"
  deb="$(mktemp --suffix=.deb)"
  curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${arch}.deb" -o "$deb"
  sudo dpkg -i "$deb" || sudo apt-get install -f -y
  rm -f "$deb"
  echo "    installed: $(cloudflared --version | head -1)"
fi

echo "==> sync (install/enable systemd units from utilities.conf)"
sudo ./sync.sh
REMOTE

# --- 5: Cloudflare Tunnel token (social-poster / Instagram) ------------------
echo
echo "==> Cloudflare Tunnel (social-poster Instagram image hosting)"

# Current token value on the Pi (empty if unset).
current_token="$(ssh "${TARGET}" "sudo grep -E '^CLOUDFLARE_TUNNEL_TOKEN=' '${ENV_FILE}'" 2>/dev/null | cut -d= -f2- || true)"

if [ -n "${current_token// /}" ]; then
  echo "    Token already set — restarting tunnel."
  ssh "${TARGET}" 'sudo systemctl restart social-poster-tunnel'
else
  cat <<'MSG'
    No tunnel token set. One-time setup in the Cloudflare Zero Trust dashboard
    (https://one.dash.cloudflare.com):
      1. Networks -> Tunnels -> Create a tunnel -> Cloudflared, name it, and copy
         the token from the shown `cloudflared ... run --token <TOKEN>` command.
      2. Under the tunnel's Public Hostnames, add:
           subdomain "poster", domain "travisbumgarner.photography",
           service Type HTTP, URL localhost:5050.
MSG
  token=""
  if { exec 3</dev/tty; } 2>/dev/null; then
    printf "    Paste tunnel token (or press Enter to skip): "
    read -rs token <&3 || token=""
    exec 3<&-
    echo
  else
    echo "    (no interactive terminal — skipping token prompt)"
  fi
  if [ -z "${token// /}" ]; then
    echo "    Skipped — Bluesky still works. Re-run ./deploy.sh to set it later."
  else
    # Pipe the token over stdin (never on the command line) and write it on the Pi.
    printf '%s' "$token" | ssh "${TARGET}" "ENV_FILE='${ENV_FILE}' bash -s" <<'REMOTE'
set -euo pipefail
TOKEN="$(cat)"
sudo ENV_FILE="$ENV_FILE" python3 - "$TOKEN" <<'PY'
import os, sys, pathlib
token = sys.argv[1].strip()
p = pathlib.Path(os.environ["ENV_FILE"])
lines = p.read_text().splitlines()
for i, ln in enumerate(lines):
    if ln.startswith("CLOUDFLARE_TUNNEL_TOKEN="):
        lines[i] = "CLOUDFLARE_TUNNEL_TOKEN=" + token
        break
else:
    lines.append("CLOUDFLARE_TUNNEL_TOKEN=" + token)
p.write_text("\n".join(lines) + "\n")
PY
sudo chmod 600 "$ENV_FILE"
sudo systemctl restart social-poster-tunnel
REMOTE
    echo "    Token saved and tunnel restarted."
  fi
fi

# Verify tunnel state (give cloudflared a few seconds to connect).
sleep 4
tunnel_state="$(ssh "${TARGET}" 'systemctl is-active social-poster-tunnel' 2>/dev/null || true)"
echo "    social-poster-tunnel: ${tunnel_state}"
if [ "${tunnel_state}" != "active" ] && [ -n "${current_token// /}${token:-}" ]; then
  echo "    Not connected yet — inspect: ssh ${TARGET} 'journalctl -u social-poster-tunnel -n 30 --no-pager'"
fi

# --- 6: final status --------------------------------------------------------
echo
ssh "${TARGET}" 'sudo "$HOME/rasppi-utils/sync.sh" --status'
echo "==> Done."
