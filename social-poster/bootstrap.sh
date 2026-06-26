#!/usr/bin/env bash
#
# DEV setup for social-poster. Run once after cloning, on your dev machine.
#
# This is for local development only. Production is a Raspberry Pi, deployed via
# the repo-root `sudo ./sync.sh` (systemd service + a permanent named Cloudflare
# Tunnel) — NOT this script. The dev/prod differences:
#
#   dev (this script)         prod (Pi, via sync.sh)
#   -----------------         ----------------------
#   config: social-poster/    config: /etc/rasppi-utils/social-poster/.env
#           config/.env               (injected by systemd)
#   data:   social-poster/    data:   /var/lib/rasppi-utils/social-poster
#           data/
#   tunnel: ephemeral quick   tunnel: permanent named tunnel (your domain),
#           tunnel started by         run as its own service
#           `npm run dev`
#
# Sets up the shared Python venv + deps, Node deps, cloudflared (for the dev
# tunnel), and a starter config/.env.
#
# Usage: ./social-poster/bootstrap.sh   (or from this dir: ./bootstrap.sh)

set -euo pipefail
cd "$(dirname "$0")"          # social-poster/
REPO_ROOT="$(cd .. && pwd)"

echo "==> Python venv + deps (shared at repo root)"
if [ ! -d "$REPO_ROOT/.venv" ]; then
  python3 -m venv "$REPO_ROOT/.venv"
fi
"$REPO_ROOT/.venv/bin/pip" install --upgrade pip
"$REPO_ROOT/.venv/bin/pip" install -r "$REPO_ROOT/requirements.txt"

echo "==> Node deps (orchestrator + web)"
npm install

echo "==> cloudflared (dev tunnel so Instagram can fetch local images)"
if command -v cloudflared >/dev/null 2>&1; then
  echo "  cloudflared already installed ($(command -v cloudflared))"
elif command -v brew >/dev/null 2>&1; then
  brew install cloudflared
else
  echo "  WARNING: cloudflared not found and Homebrew unavailable."
  echo "  Install it from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  echo "  (dev still runs without it, but live Instagram posts won't — DRY_RUN only)."
fi

echo "==> Dev config (config/.env)"
if [ -f config/.env ]; then
  echo "  config/.env already exists — leaving it as-is"
else
  cp config/.env.example config/.env
  echo "  created config/.env from the example — edit it and set DRY_RUN=1 for safe dev"
fi

echo
echo "Done. Start dev with:"
echo "  cd social-poster && npm run dev   # quick tunnel + Flask :5050 + Vite :5173"
echo
echo "For safe local testing set DRY_RUN=1 in config/.env (simulates posting)."
echo "Add Instagram/Bluesky accounts in the web UI (Accounts panel), not the .env."
