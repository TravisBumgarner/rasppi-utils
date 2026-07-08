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
#   BRANCH=my-feature ./deploy.sh     # deploy a branch instead of the Pi's current one
#
set -euo pipefail

TARGET="${1:-motioncam@motioncam.local}"
REPO_URL="${REPO_URL:-https://github.com/TravisBumgarner/rasppi-utils.git}"
BRANCH="${BRANCH:-}"

echo "==> Deploying to ${TARGET}${BRANCH:+ (branch: ${BRANCH})}"

# --- 1-4: code, deps, cloudflared, sync -------------------------------------
ssh "${TARGET}" REPO_URL="${REPO_URL}" BRANCH="${BRANCH}" 'bash -s' <<'REMOTE'
set -euo pipefail
cd "$HOME"

echo "==> Repo"
if [ -d rasppi-utils/.git ]; then
  if [ -n "$BRANCH" ]; then
    git -C rasppi-utils fetch origin "$BRANCH"
    git -C rasppi-utils checkout "$BRANCH"
  fi
  git -C rasppi-utils pull --ff-only
else
  git clone "$REPO_URL" rasppi-utils
  [ -z "$BRANCH" ] || git -C rasppi-utils checkout "$BRANCH"
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

# --- 5: Cloudflare Tunnel (social-poster / Instagram) ------------------------
echo
echo "==> Cloudflare Tunnel (social-poster Instagram image hosting)"

tunnel_state="$(ssh "${TARGET}" 'systemctl is-active social-poster-tunnel' 2>/dev/null || true)"
configured="$(ssh "${TARGET}" 'test -f /etc/cloudflared/config.yml && echo yes || echo no')"

if [ "${configured}" = "yes" ]; then
  ssh "${TARGET}" 'sudo systemctl restart social-poster-tunnel' || true
  sleep 4
  tunnel_state="$(ssh "${TARGET}" 'systemctl is-active social-poster-tunnel' 2>/dev/null || true)"
  echo "    Configured. social-poster-tunnel: ${tunnel_state}"
  if [ "${tunnel_state}" != "active" ]; then
    echo "    Not connected — inspect: ssh ${TARGET} 'journalctl -u social-poster-tunnel -n 30 --no-pager'"
  fi
else
  cat <<MSG
    Instagram needs a public URL via a Cloudflare Tunnel, which isn't set up yet.
    It's a one-time step (needs a browser authorization for your domain). Run:

      ssh ${TARGET}
      ~/rasppi-utils/social-poster/setup-cloudflare.sh

    Bluesky posting works without it.
MSG
fi

# --- 6: final status --------------------------------------------------------
echo
ssh "${TARGET}" 'sudo "$HOME/rasppi-utils/sync.sh" --status'
echo "==> Done."
