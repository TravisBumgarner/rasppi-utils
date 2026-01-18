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

### Step 1: Prepare Your Raspberry Pi

Ensure your Pi is up to date:

```bash
sudo apt update && sudo apt full-upgrade -y
```

### Step 2: Set Up SSH Key for GitHub

Since this is a private repository, you need an SSH key to clone it.

**Generate an SSH key:**

```bash
ssh-keygen -t ed25519 -C "raspberrypi"
```

Press Enter to accept the default location and optionally set a passphrase.

**Display your public key:**

```bash
cat ~/.ssh/id_ed25519.pub
```

**Add the key to GitHub:**

1. Go to [GitHub SSH Keys Settings](https://github.com/settings/keys)
2. Click "New SSH key"
3. Give it a title (e.g., "Raspberry Pi")
4. Paste your public key
5. Click "Add SSH key"

**Test the connection:**

```bash
ssh -T git@github.com
```

You should see: "Hi username! You've successfully authenticated..."

### Step 3: Clone and Bootstrap

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

The repository can be cloned to any location - the scripts use their own directory as the installation path.

During the sync process, you'll be prompted to configure any enabled utilities that don't have configuration yet.

## Managing Utilities

### Enable/Disable Utilities

Edit `utilities.conf` to control which utilities are active:

```bash
sudo nano ~/rasppi-utils/utilities.conf
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

View the status of all utilities and their systemd services:

```bash
sudo ~/rasppi-utils/sync.sh --status
```

## Utility Configuration

### supabase-keepalive

Prevents Supabase free-tier projects from pausing by making a daily API call.

**Configuration:**

The configuration is stored at `/etc/rasppi-utils/supabase-keepalive/.env`

Required settings:
- `SUPABASE_URL`: Your Supabase project URL (e.g., `https://your-project.supabase.co`)
- `SUPABASE_KEY`: Your Supabase anon/public key

**Get your credentials:**

1. Go to your [Supabase Dashboard](https://app.supabase.com/)
2. Select your project
3. Go to Settings > API
4. Copy the "Project URL" and "anon public" key

**Schedule:**

Runs daily via systemd timer with a randomized delay of up to 1 hour.

## Troubleshooting

### View Service Logs

```bash
# View recent logs for a specific service
sudo journalctl -u supabase-keepalive.service -n 50

# Follow logs in real-time
sudo journalctl -u supabase-keepalive.service -f

# View timer status
sudo systemctl status supabase-keepalive.timer
```

### Manually Run a Utility

```bash
# Run the keepalive script manually
sudo ~/rasppi-utils/.venv/bin/python ~/rasppi-utils/supabase-keepalive/scripts/keepalive.py
```

### Check Timer Schedule

```bash
# List all timers and when they'll run next
sudo systemctl list-timers

# Check specific timer
sudo systemctl status supabase-keepalive.timer
```

### Common Issues

**Service fails to start:**
- Check the logs with `journalctl`
- Verify configuration exists at `/etc/rasppi-utils/<utility>/.env`
- Ensure the virtual environment is set up: `~/rasppi-utils/.venv/`

**GitHub clone fails:**
- Verify SSH key is added to GitHub
- Test connection: `ssh -T git@github.com`
- Check SSH key permissions: `chmod 600 ~/.ssh/id_ed25519`

## Updating

To update to the latest version:

```bash
cd ~/rasppi-utils
git pull
sudo ./bootstrap.sh
```

This will:
- Pull the latest code
- Update Python dependencies if needed
- Re-sync utilities (preserving your configuration)

## Project Structure

```
rasppi-utils/
├── bootstrap.sh              # One-time Pi setup
├── sync.sh                   # Utility management
├── utilities.conf            # Which utilities are enabled
├── requirements.txt          # Python dependencies
├── supabase-keepalive/       # Self-contained utility
│   ├── scripts/
│   │   └── keepalive.py
│   ├── config/
│   │   └── .env.example
│   └── systemd/
│       ├── supabase-keepalive.service
│       └── supabase-keepalive.timer
└── tests/
    └── supabase-keepalive/
        └── test_keepalive.py
```

## Adding New Utilities

Each utility follows this structure:

```
utility-name/
├── scripts/           # Executable scripts
│   └── main.py
├── config/
│   └── .env.example   # Configuration template
└── systemd/
    ├── utility-name.service
    └── utility-name.timer    # Optional, for scheduled tasks
```

To add a new utility:
1. Create the directory structure
2. Add systemd units using `{{INSTALL_DIR}}` placeholder for paths (will be replaced during installation)
3. Add the utility name to `utilities.conf`
4. Run `sudo ./sync.sh`
