#!/usr/bin/env python3
"""Status Dashboard - Web interface for rasppi-utils."""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify

app = Flask(__name__)

# Find the project root (parent of status-dashboard)
SCRIPT_DIR = Path(__file__).parent.parent.parent
UTILITIES_CONF = SCRIPT_DIR / "utilities.conf"


def get_enabled_utilities() -> list[str]:
    """Read utilities.conf and return list of enabled utility names."""
    utilities = []
    if not UTILITIES_CONF.exists():
        return utilities

    with open(UTILITIES_CONF) as f:
        for line in f:
            # Strip whitespace and skip comments/empty lines
            line = line.strip()
            if line and not line.startswith("#"):
                utilities.append(line)

    return utilities


def get_unit_status(unit_name: str) -> dict:
    """Get status of a systemd unit (service or timer)."""
    result = {
        "name": unit_name,
        "active": "unknown",
        "enabled": "unknown",
    }

    try:
        active_result = subprocess.run(
            ["systemctl", "is-active", unit_name],
            capture_output=True,
            text=True,
        )
        result["active"] = active_result.stdout.strip() or "inactive"
    except Exception:
        result["active"] = "error"

    try:
        enabled_result = subprocess.run(
            ["systemctl", "is-enabled", unit_name],
            capture_output=True,
            text=True,
        )
        result["enabled"] = enabled_result.stdout.strip() or "disabled"
    except Exception:
        result["enabled"] = "error"

    return result


def get_utility_status(utility: str) -> dict:
    """Get full status for a utility including its services and timers."""
    service_name = f"{utility}.service"
    timer_name = f"{utility}.timer"

    status = {
        "name": utility,
        "enabled": True,
        "services": [get_unit_status(service_name)],
        "timers": [],
    }

    # Check if timer exists by trying to get its status
    timer_status = get_unit_status(timer_name)
    # Only include timer if it's not "not-found"
    if timer_status["enabled"] not in ("not-found", "error"):
        status["timers"].append(timer_status)

    return status


def get_all_status() -> dict:
    """Get status of all enabled utilities."""
    utilities = get_enabled_utilities()
    return {
        "utilities": [get_utility_status(u) for u in utilities]
    }


def get_logs(utility: str, count: int = 50) -> dict:
    """Get recent logs for a utility from journalctl."""
    service_name = f"{utility}.service"
    entries = []

    try:
        result = subprocess.run(
            [
                "journalctl",
                "-u", service_name,
                "--no-pager",
                "-n", str(count),
                "--output=json",
            ],
            capture_output=True,
            text=True,
        )

        # journalctl --output=json outputs one JSON object per line
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                entry = json.loads(line)
                # Convert timestamp (microseconds since epoch) to ISO format
                timestamp_us = int(entry.get("__REALTIME_TIMESTAMP", 0))
                timestamp = datetime.fromtimestamp(timestamp_us / 1_000_000)
                entries.append({
                    "timestamp": timestamp.isoformat(),
                    "message": entry.get("MESSAGE", ""),
                })
            except (json.JSONDecodeError, ValueError):
                continue

    except Exception as e:
        return {
            "utility": utility,
            "error": str(e),
            "entries": [],
        }

    return {
        "utility": utility,
        "entries": entries,
    }


# HTML template for the dashboard
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>rasppi-utils Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
            min-height: 100vh;
        }
        h1 {
            text-align: center;
            margin-bottom: 20px;
            color: #00d9ff;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .controls {
            text-align: center;
            margin-bottom: 20px;
        }
        button {
            background: #00d9ff;
            color: #1a1a2e;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
        }
        button:hover { background: #00b8d9; }
        .utilities {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .utility-card {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .utility-card:hover { transform: translateY(-2px); }
        .utility-card.selected { border: 2px solid #00d9ff; }
        .utility-name {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #00d9ff;
        }
        .unit {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #2a2a4a;
        }
        .unit:last-child { border-bottom: none; }
        .unit-name { font-size: 13px; color: #aaa; }
        .status-badges { display: flex; gap: 8px; }
        .badge {
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .badge.active { background: #00c853; color: #000; }
        .badge.inactive { background: #ff5252; color: #fff; }
        .badge.enabled { background: #2196f3; color: #fff; }
        .badge.disabled { background: #757575; color: #fff; }
        .badge.unknown { background: #ff9800; color: #000; }
        .logs-panel {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
        }
        .logs-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .logs-title { font-size: 18px; color: #00d9ff; }
        .logs-container {
            background: #0d1117;
            border-radius: 5px;
            padding: 15px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 12px;
        }
        .log-entry {
            padding: 5px 0;
            border-bottom: 1px solid #2a2a4a;
        }
        .log-entry:last-child { border-bottom: none; }
        .log-time { color: #888; margin-right: 10px; }
        .log-message { color: #ddd; }
        .no-logs { color: #888; font-style: italic; }
        .last-updated {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>rasppi-utils Dashboard</h1>
        <div class="controls">
            <button onclick="refresh()">Refresh Now</button>
        </div>
        <div class="utilities" id="utilities"></div>
        <div class="logs-panel">
            <div class="logs-header">
                <span class="logs-title">Logs: <span id="selected-utility">Select a utility</span></span>
            </div>
            <div class="logs-container" id="logs">
                <div class="no-logs">Click on a utility card to view its logs</div>
            </div>
        </div>
        <div class="last-updated">Last updated: <span id="last-updated">-</span></div>
    </div>

    <script>
        let selectedUtility = null;

        function getBadgeClass(value) {
            if (value === 'active') return 'active';
            if (value === 'inactive') return 'inactive';
            if (value === 'enabled') return 'enabled';
            if (value === 'disabled') return 'disabled';
            return 'unknown';
        }

        async function fetchStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                renderUtilities(data.utilities);
                document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Failed to fetch status:', error);
            }
        }

        function renderUtilities(utilities) {
            const container = document.getElementById('utilities');
            container.innerHTML = utilities.map(u => `
                <div class="utility-card ${selectedUtility === u.name ? 'selected' : ''}"
                     onclick="selectUtility('${u.name}')">
                    <div class="utility-name">${u.name}</div>
                    ${u.services.map(s => `
                        <div class="unit">
                            <span class="unit-name">${s.name}</span>
                            <div class="status-badges">
                                <span class="badge ${getBadgeClass(s.active)}">${s.active}</span>
                                <span class="badge ${getBadgeClass(s.enabled)}">${s.enabled}</span>
                            </div>
                        </div>
                    `).join('')}
                    ${u.timers.map(t => `
                        <div class="unit">
                            <span class="unit-name">${t.name}</span>
                            <div class="status-badges">
                                <span class="badge ${getBadgeClass(t.active)}">${t.active}</span>
                                <span class="badge ${getBadgeClass(t.enabled)}">${t.enabled}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `).join('');
        }

        async function selectUtility(name) {
            selectedUtility = name;
            document.getElementById('selected-utility').textContent = name;
            document.querySelectorAll('.utility-card').forEach(card => {
                card.classList.toggle('selected', card.querySelector('.utility-name').textContent === name);
            });
            await fetchLogs(name);
        }

        async function fetchLogs(utility) {
            try {
                const response = await fetch(`/api/logs/${utility}`);
                const data = await response.json();
                renderLogs(data);
            } catch (error) {
                console.error('Failed to fetch logs:', error);
            }
        }

        function renderLogs(data) {
            const container = document.getElementById('logs');
            if (data.error) {
                container.innerHTML = `<div class="no-logs">Error: ${data.error}</div>`;
                return;
            }
            if (data.entries.length === 0) {
                container.innerHTML = '<div class="no-logs">No logs found</div>';
                return;
            }
            container.innerHTML = data.entries.map(e => `
                <div class="log-entry">
                    <span class="log-time">${new Date(e.timestamp).toLocaleString()}</span>
                    <span class="log-message">${escapeHtml(e.message)}</span>
                </div>
            `).join('');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function refresh() {
            fetchStatus();
            if (selectedUtility) {
                fetchLogs(selectedUtility);
            }
        }

        // Initial load
        fetchStatus();

        // Auto-refresh every 30 seconds
        setInterval(fetchStatus, 30000);
    </script>
</body>
</html>
"""


@app.route("/")
def dashboard():
    """Serve the HTML dashboard."""
    return DASHBOARD_HTML


@app.route("/api/status")
def api_status():
    """Return JSON status of all utilities."""
    return jsonify(get_all_status())


@app.route("/api/logs/<utility>")
def api_logs(utility: str):
    """Return JSON logs for a specific utility."""
    # Basic validation - only allow alphanumeric and hyphens
    if not all(c.isalnum() or c == "-" for c in utility):
        return jsonify({"error": "Invalid utility name"}), 400
    return jsonify(get_logs(utility))


def main():
    """Run the Flask development server."""
    port = int(os.environ.get("PORT", 8080))
    # Bind to all interfaces so it's accessible on local network
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
