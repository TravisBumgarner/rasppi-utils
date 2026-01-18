# Modular Refactor

## Overview

Refactor rasppi-utils to have a modular, utility-first architecture where each utility is self-contained in its own directory. Split the monolithic bootstrap.sh into two scripts: one for initial Pi setup and one for managing which utilities are enabled.

## Goals

- Reorganize to utility-first directory structure (each utility contains its own scripts, config, systemd units)
- Split bootstrap into two concerns: Pi setup vs utility management
- Create comprehensive README with full setup instructions including SSH for private repo access
- Make it easy to add new utilities following a consistent pattern

## Non-Goals

- Adding new utilities (this refactor just reorganizes existing code)
- Changing the functionality of supabase-keepalive itself

## Current Structure

```
rasppi-utils/
├── bootstrap.sh           # Does everything (setup + enable all)
├── scripts/
│   └── supabase_keepalive.py
├── config/
│   └── .env.example
├── systemd/
│   ├── supabase-keepalive.service
│   └── supabase-keepalive.timer
└── README.md              # Minimal
```

## New Structure

```
rasppi-utils/
├── bootstrap.sh                    # One-time Pi setup only
├── sync.sh                         # Enable/disable utilities, sync to systemd
├── utilities.conf                  # Which utilities are enabled
├── supabase-keepalive/             # Self-contained utility
│   ├── scripts/
│   │   └── keepalive.py
│   ├── config/
│   │   └── .env.example
│   └── systemd/
│       ├── supabase-keepalive.service
│       └── supabase-keepalive.timer
├── tests/
│   └── supabase-keepalive/
│       └── test_keepalive.py
└── README.md                       # Comprehensive setup guide
```

## Technical Design

### 1. bootstrap.sh (One-Time Pi Setup)

Responsibilities:
- Install system dependencies (python3, pip, venv, git)
- Set up SSH key for GitHub (for private repo access)
- Clone/update the repo to /opt/rasppi-utils
- Create Python virtual environment
- Install Python dependencies
- Create /etc/rasppi-utils/ config directory
- Run sync.sh at the end

This script is run once when setting up a new Pi, or when you want to update the installation.

### 2. sync.sh (Utility Management)

Responsibilities:
- Read utilities.conf to determine which utilities are enabled
- For each enabled utility:
  - Prompt for config if not already configured
  - Copy systemd units to /etc/systemd/system/
  - Enable and start timers/services
- For each disabled utility:
  - Stop and disable timers/services
  - Remove systemd units from /etc/systemd/system/
- Reload systemd daemon

Usage:
```bash
sudo ./sync.sh              # Sync all utilities based on utilities.conf
sudo ./sync.sh --status     # Show status of all utilities
```

### 3. utilities.conf

Simple config file listing enabled utilities:

```
# Enabled utilities (one per line)
# Comment out or remove to disable

supabase-keepalive
# future-utility
```

### 4. Utility Directory Structure

Each utility follows this pattern:

```
utility-name/
├── scripts/           # Python/bash scripts
│   └── main.py        # Main executable
├── config/
│   └── .env.example   # Config template
└── systemd/
    ├── utility-name.service
    └── utility-name.timer    # If scheduled
```

The systemd units reference paths like:
- `/opt/rasppi-utils/utility-name/scripts/main.py`
- `/etc/rasppi-utils/utility-name/.env`

### 5. README.md

Full setup guide including:

1. **Prerequisites**
   - Raspberry Pi with Raspberry Pi OS
   - Internet connection
   - GitHub account with access to this private repo

2. **Generate SSH Key on Pi**
   ```bash
   ssh-keygen -t ed25519 -C "raspberrypi"
   cat ~/.ssh/id_ed25519.pub
   ```
   Add this key to GitHub: Settings > SSH Keys

3. **Clone and Bootstrap**
   ```bash
   git clone git@github.com:travisbumgarner/rasppi-utils.git
   cd rasppi-utils
   sudo ./bootstrap.sh
   ```

4. **Configure Utilities**
   - Edit utilities.conf to enable/disable utilities
   - Run `sudo ./sync.sh` to apply changes

5. **Utility-Specific Configuration**
   - Each utility's config section with credentials/settings

6. **Managing Utilities**
   - How to check status
   - How to view logs
   - How to manually run

7. **Updating**
   ```bash
   cd /opt/rasppi-utils
   sudo git pull
   sudo ./bootstrap.sh
   ```

## Migration Path

1. Create new directory structure
2. Move supabase-keepalive files to new location
3. Update systemd unit paths
4. Rewrite bootstrap.sh for new responsibilities
5. Create sync.sh
6. Create utilities.conf
7. Update tests for new paths
8. Write comprehensive README

## Dependencies

- git (for cloning private repo)
- python3, python3-pip, python3-venv
- rsync (for file sync)
