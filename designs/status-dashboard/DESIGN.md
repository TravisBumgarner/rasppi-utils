# Status Dashboard

## Overview

A simple web server utility that provides a dashboard to view the status of enabled utilities and their logs. This gives visibility into what's running on the Pi without needing to SSH in and run commands.

## Goals

- Display status of all enabled utilities (running, stopped, enabled, disabled)
- View recent logs for each utility
- Simple, lightweight web interface accessible from local network
- Follow existing utility pattern (scripts/, config/, systemd/)

## Non-Goals

- Authentication (assume trusted local network)
- Log persistence beyond systemd journal
- Real-time log streaming (polling is sufficient)
- Control actions (start/stop services) - read-only for safety

## Technical Design

### Utility Structure

```
status-dashboard/
├── scripts/
│   └── server.py          # Flask web server
├── config/
│   └── .env.example       # PORT configuration
└── systemd/
    └── status-dashboard.service   # Long-running service (no timer)
```

### Configuration

`.env.example`:
```
# Port for the dashboard web server
PORT=8080
```

### API Endpoints

1. **GET /** - HTML dashboard page
2. **GET /api/status** - JSON status of all utilities
3. **GET /api/logs/<utility>** - JSON recent logs for a utility

### Status Response Format

```json
{
  "utilities": [
    {
      "name": "supabase-keepalive",
      "enabled": true,
      "services": [
        {
          "name": "supabase-keepalive.service",
          "active": "inactive",
          "enabled": "enabled"
        }
      ],
      "timers": [
        {
          "name": "supabase-keepalive.timer",
          "active": "active",
          "enabled": "enabled"
        }
      ]
    }
  ]
}
```

### Logs Response Format

```json
{
  "utility": "supabase-keepalive",
  "entries": [
    {
      "timestamp": "2026-01-18T12:00:00",
      "message": "Supabase keep-alive ping successful"
    }
  ]
}
```

### HTML Dashboard

Simple single-page layout:
- Header with "rasppi-utils Dashboard"
- Status cards for each utility showing service/timer states
- Log viewer panel that shows logs when a utility is selected
- Auto-refresh every 30 seconds (or manual refresh button)

### Implementation Notes

1. **Status retrieval**: Use `systemctl is-active` and `systemctl is-enabled` commands via subprocess
2. **Log retrieval**: Use `journalctl -u <service> --no-pager -n 50 --output=json` for structured output
3. **Web framework**: Flask (lightweight, sufficient for this use case)
4. **HTML**: Inline in Python or simple Jinja2 template - keep it minimal

### Systemd Service

```ini
[Unit]
Description=Status Dashboard - Web interface for rasppi-utils
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={{INSTALL_DIR}}/status-dashboard
ExecStart={{INSTALL_DIR}}/.venv/bin/python {{INSTALL_DIR}}/status-dashboard/scripts/server.py
EnvironmentFile=/etc/rasppi-utils/status-dashboard/.env
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Dependencies

- Flask (add to requirements.txt)

## Security Considerations

- Binds to 0.0.0.0 by default (accessible on local network)
- No authentication - suitable for home/trusted networks only
- Read-only - cannot modify system state
- Runs as root to access journalctl (same as other utilities)
