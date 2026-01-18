# rasppi-utils

A collection of utilities for Raspberry Pi, designed with a modular architecture where each utility is self-contained and can be independently enabled or disabled.

## Overview

This repository provides automated scripts that run on a Raspberry Pi to perform various background tasks. Currently includes:

- **supabase-keepalive**: Prevents Supabase free-tier projects from pausing due to inactivity by making daily API calls

## Prerequisites

- Raspberry Pi with Raspberry Pi OS (or other Debian-based OS)
- Internet connection
- GitHub account with access to this private repository

## Installation

### Step 1: Set Up SSH Key for GitHub

Since this is a private repository, you need an SSH key to clone it.

```bash
# Generate an SSH key
ssh-keygen -t ed25519 -C "raspberrypi"

# Display your public key
cat ~/.ssh/id_ed25519.pub
```

Add the key to GitHub:
1. Go to [GitHub SSH Keys Settings](https://github.com/settings/keys)
2. Click "New SSH key"
3. Paste your public key and save

Test the connection:
```bash
ssh -T git@github.com
```

### Step 2: Clone and Bootstrap

```bash
cd ~
git clone git@github.com:travisbumgarner/rasppi-utils.git
cd rasppi-utils
sudo ./bootstrap.sh
```

The bootstrap script will:
- Install system dependencies (python3, pip, venv)
- Set up the Python virtual environment
- Install Python dependencies
- Create the configuration directory at `/etc/rasppi-utils/`
- Run `sync.sh` to configure enabled utilities

During the sync process, you'll be prompted to configure any enabled utilities.

## Managing Utilities

### Enable/Disable Utilities

Edit `utilities.conf` to control which utilities are active:

```bash
nano ~/rasppi-utils/utilities.conf
```

```
# Enabled utilities (one per line)
# Comment out or remove a line to disable that utility

supabase-keepalive
# future-utility
```

After editing, apply changes:

```bash
sudo ~/rasppi-utils/sync.sh
```

### Check Utility Status

```bash
sudo ~/rasppi-utils/sync.sh --status
```

## Utility Configuration

### supabase-keepalive

Prevents Supabase free-tier projects from pausing by making a daily API call.

**Configuration** is stored at `/etc/rasppi-utils/supabase-keepalive/.env`

Required settings:
- `SUPABASE_URL`: Your Supabase project URL (e.g., `https://your-project.supabase.co`)
- `SUPABASE_KEY`: Your Supabase anon/public key

Get your credentials from [Supabase Dashboard](https://app.supabase.com/) > Project > Settings > API

**Schedule:** Runs daily via systemd timer with a randomized delay of up to 1 hour.

## Troubleshooting

### View Service Logs

```bash
# View recent logs
sudo journalctl -u supabase-keepalive.service -n 50

# Follow logs in real-time
sudo journalctl -u supabase-keepalive.service -f
```

### Check Timer Status

```bash
sudo systemctl list-timers
sudo systemctl status supabase-keepalive.timer
```

### Manually Run a Utility

```bash
sudo ~/rasppi-utils/.venv/bin/python ~/rasppi-utils/supabase-keepalive/scripts/keepalive.py
```

### Common Issues

**Service fails to start:**
- Check logs with `journalctl`
- Verify configuration exists at `/etc/rasppi-utils/<utility>/.env`

**GitHub clone fails:**
- Test SSH connection: `ssh -T git@github.com`
- Check key permissions: `chmod 600 ~/.ssh/id_ed25519`

## Updating

```bash
cd ~/rasppi-utils
git pull
sudo ./bootstrap.sh
```

## Project Structure

```
rasppi-utils/
├── bootstrap.sh              # One-time setup
├── sync.sh                   # Utility management
├── utilities.conf            # Enabled utilities
├── requirements.txt          # Python dependencies
└── supabase-keepalive/       # Self-contained utility
    ├── scripts/
    │   └── keepalive.py
    ├── config/
    │   └── .env.example
    └── systemd/
        ├── supabase-keepalive.service
        └── supabase-keepalive.timer
```
