# Initial Scaffolding

## Overview

A collection of utility scripts for Raspberry Pi that run as systemd services/timers. Includes a bootstrapping mechanism to set up a new Pi and install all services.

## Goals

- Create a main bootstrap script that sets up a new Raspberry Pi with all utilities
- Establish a pattern for adding systemd-based scheduled tasks
- Implement the first utility: Supabase keep-alive to prevent free-tier project pausing

## Non-Goals

- GUI or web interface
- Using third-party keep-alive libraries or services
- Supporting non-Raspberry Pi systems (though it may work on other Linux)

## Technical Design

### Architecture

```
rasppi-utils/
├── bootstrap.sh           # Main entry point - sets up Pi and installs services
├── scripts/
│   └── supabase-keepalive.py   # Keep-alive script using official supabase-py
├── systemd/
│   ├── supabase-keepalive.service  # oneshot service
│   └── supabase-keepalive.timer    # daily timer
├── config/
│   └── .env.example       # Template for credentials
└── requirements.txt       # Python dependencies
```

### Components

#### 1. Bootstrap Script (`bootstrap.sh`)

Shell script that:
- Installs system dependencies (Python 3, pip)
- Creates a Python virtual environment
- Installs Python dependencies from requirements.txt
- Copies systemd unit files to `/etc/systemd/system/`
- Prompts user for credentials and creates config file
- Enables and starts systemd timers

#### 2. Supabase Keep-Alive Script (`scripts/supabase-keepalive.py`)

Python script that:
- Loads credentials from environment or config file
- Connects to Supabase using official `supabase-py` client
- Executes a simple query (e.g., `SELECT 1` or query a health-check table)
- Logs success/failure
- Exits with appropriate code for systemd

#### 3. Systemd Units

**Service** (`supabase-keepalive.service`):
- Type: oneshot
- Runs the Python script with the virtual environment
- WorkingDirectory set to project root

**Timer** (`supabase-keepalive.timer`):
- Runs once daily
- Persistent=true (runs missed executions after reboot)

### Configuration

Credentials stored in `/etc/rasppi-utils/.env` or `~/.config/rasppi-utils/.env`:
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key
```

## Dependencies

- Python 3.8+
- `supabase` (official Python client)
- `python-dotenv` (for loading .env files)

## Testing Strategy

- Unit tests for the keep-alive script (mock Supabase client)
- Manual integration test with real Supabase credentials

## References

- [Supabase Python Client Docs](https://supabase.com/docs/reference/python/introduction)
- [supabase-py GitHub](https://github.com/supabase/supabase-py)
- [systemd Timer Documentation](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)
