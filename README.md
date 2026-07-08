# rasppi-utils

A modular collection of background utilities for a Raspberry Pi. Each utility is self-contained and can be enabled/disabled independently.

- **supabase-keepalive** — daily API call to keep a Supabase free-tier project from pausing.
- **status-dashboard** — read-only web page showing utility status and logs.
- **pixels64** — hosts the Web Bluetooth UI for controlling the Pixels64 LED display.
- **social-poster** — schedule image posts to Instagram/Bluesky from a calendar/queue web app.
- **contest-scout** — monthly headless-Claude sweep for photo contests; updates the deadlines doc and pings the contact-form relay.

## Setup

### On the Pi

SSH in (or use a keyboard/monitor), clone the repo, and run the Pi bootstrap:

```bash
git clone git@github.com:travisbumgarner/rasppi-utils.git ~/rasppi-utils
cd ~/rasppi-utils
sudo ./bootstrap-pi.sh
```

`bootstrap-pi.sh` sets the hostname to `rasppi-utils`, creates a `rasppi-utils` user (password `rasppi-utils`), installs dependencies, and configures enabled utilities. You'll be prompted for any missing utility config.

> Private repo — you need an SSH key on the Pi added to GitHub. See [GitHub's guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh).

### From your laptop

Once the Pi is bootstrapped, connect with:

```bash
./bootstrap-client.sh
```

This SSHes into `rasppi-utils@rasppi-utils.local`. If `.local` doesn't resolve, it falls back to [`find-pi.sh`](find-pi.sh) to locate the Pi by IP.

## Managing utilities

Enabled utilities are listed in [`utilities.conf`](utilities.conf), one per line (comment out to disable):

```bash
sudo nano ~/rasppi-utils/utilities.conf
sudo ~/rasppi-utils/sync.sh           # apply changes
sudo ~/rasppi-utils/sync.sh --status  # check status
```

## Configuration

Config lives at `/etc/rasppi-utils/<utility>/.env`.

| Utility | Settings |
|---|---|
| `supabase-keepalive` | `SUPABASE_URL`, `SUPABASE_KEY` (Supabase Dashboard → Settings → API). Runs daily via systemd timer. |
| `status-dashboard` | `PORT` (default `80`). Access at `http://rasppi-utils.local`. No auth — trusted networks only. |
| `pixels64` | `PORT` (default `8443`). Access at `https://rasppi-utils.local:8443` in Chrome/Edge. HTTPS with a self-signed cert (one-time browser warning) — required for Web Bluetooth. The page connects to your ESP32 boards directly over Bluetooth. |
| `contest-scout` | `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or `ANTHROPIC_API_KEY`; optional `CLAUDE_BIN`, `CONTACT_FORM_URL`. Monthly systemd timer runs the repo's `/find-contests` skill headless, updates the live deadlines file in `/var/lib/rasppi-utils/contest-scout` (unversioned; seeded from the repo copy), and sends the summary through the contact-form relay ("Time for monthly contests"). Claude CLI installed by `bootstrap-pi.sh` — see [contest-scout/README.md](contest-scout/README.md). |
| `social-poster` | `PORT` (default `5050`), `PUBLIC_BASE_URL` (Instagram tunnel — see [setup](#social-poster-frontend)). Access at `http://rasppi-utils.local:5050`. Upload an image, pick accounts, schedule on a calendar; a per-minute timer publishes due posts. Add Instagram (user ID + long-lived access token, Graph API) and Bluesky (handle + app password) accounts in the UI. Data in `/var/lib/rasppi-utils/social-poster`. Instagram needs a public image URL, so a Cloudflare Tunnel (`social-poster-tunnel` service) exposes this app; Bluesky works without it. |

## Updating

From your laptop (pulls latest, refreshes the venv/cloudflared, runs `sync.sh`, and prompts for the social-poster tunnel token if unset):

```bash
./deploy.sh                       # defaults to motioncam@motioncam.local
./deploy.sh pi@raspberrypi.local  # custom user@host
```

Or directly on the Pi:

```bash
cd ~/rasppi-utils && git pull && sudo ./bootstrap-pi.sh
```

## Troubleshooting

```bash
sudo journalctl -u <utility>.service -n 50   # recent logs
sudo journalctl -u <utility>.service -f      # follow logs
sudo systemctl list-timers                   # scheduled runs
```

If a service won't start, check the logs and confirm its config exists at `/etc/rasppi-utils/<utility>/.env`.

## Adding a utility

Each utility is a directory:

```
utility-name/
├── scripts/         # executable scripts
├── config/.env.example
└── systemd/         # *.service (+ optional *.timer), use {{INSTALL_DIR}} for paths
```

Create it, add its name to `utilities.conf`, then run `sudo ./sync.sh`.

## social-poster frontend

The web app is React/TS (Vite). The Pi serves the prebuilt bundle and needs no Node toolchain, so `web/dist/` is committed.

Dev (needs the repo `.venv` set up — see Setup):

```bash
cd social-poster
npm install      # concurrently + web deps
npm run dev      # Flask :5050 + Vite :5173 together (open http://localhost:5173)
npm run build    # rebuild web/dist/ before committing UI changes
```

A pre-commit hook (`.githooks/pre-commit`) rebuilds `web/dist/` automatically when you commit changes under `web/src`. Enable it once per clone with `git config core.hooksPath .githooks`.

### Instagram tunnel (production)

Instagram's Graph API fetches each photo from a public URL, so the Pi must be reachable from the internet. We use a named Cloudflare Tunnel (no open ports) run by the `social-poster-tunnel` systemd service. One-time setup, run on the Pi:

```bash
ssh motioncam@motioncam.local
~/rasppi-utils/social-poster/setup-cloudflare.sh
```

It opens a browser URL to authorize your domain once, then creates the tunnel, **auto-creates the DNS record**, writes `/etc/cloudflared/config.yml`, and starts the service. Override defaults with env vars if needed: `TUNNEL_NAME`, `HOSTNAME_FQDN`, `LOCAL_URL`.

Bluesky posting works without any of this; only Instagram needs the tunnel. Set `DRY_RUN=1` to exercise the UI/scheduler without sending real posts.
