#!/usr/bin/env python3
"""Status Dashboard - Web interface for rasppi-utils."""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

# Find the project root (parent of status-dashboard)
SCRIPT_DIR = Path(__file__).parent.parent.parent
UTILITIES_CONF = SCRIPT_DIR / "utilities.conf"
CONFIG_DIR = Path("/etc/rasppi-utils")

# Monthly HTML contest reports written by contest-scout's sweep. Viewing has
# zero dependency on that job: until it has ever run, /contests serves the
# HTML page shipped in the repo.
CONTEST_REPORTS_DIR = Path(
    os.environ.get(
        "CONTEST_REPORTS_DIR", "/var/lib/rasppi-utils/contest-scout/reports"
    )
)
CONTEST_SEED_HTML = SCRIPT_DIR / "contest-scout" / "contests.html"

# Utilities that expose a web UI. The port is read from the utility's installed
# .env (falling back to default_port); scheme is fixed per utility. A "path"
# entry means the page is served by this dashboard itself (same host/port).
# Utilities absent here (e.g. supabase-keepalive) get no link.
WEB_UIS = {
    "social-poster": {"scheme": "http", "default_port": 5050},
    "pixels64": {"scheme": "https", "default_port": 8443},
    # Monthly contest reports, served by this dashboard at /contests.
    "contest-scout": {"path": "/contests"},
}


def get_web_ui(utility: str) -> Optional[dict]:
    """Return {scheme, port} or {path} for a utility's web UI, or None."""
    spec = WEB_UIS.get(utility)
    if not spec:
        return None
    if "path" in spec:
        return {"path": spec["path"]}
    port = spec["default_port"]
    env_file = CONFIG_DIR / utility / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("PORT="):
                value = line.split("=", 1)[1].strip()
                if value.isdigit():
                    port = int(value)
                break
    return {"scheme": spec["scheme"], "port": port}


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
        "web": get_web_ui(utility),
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
        .utility-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .utility-name {
            font-size: 18px;
            font-weight: bold;
            color: #00d9ff;
        }
        .run-btn {
            background: #4caf50;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
        }
        .run-btn:hover { background: #45a049; }
        .run-btn:disabled { background: #666; cursor: not-allowed; }
        .card-actions { display: flex; gap: 8px; align-items: center; }
        .open-btn {
            background: #00d9ff;
            color: #1a1a2e;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            text-decoration: none;
            white-space: nowrap;
        }
        .open-btn:hover { background: #00b8d9; }
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

        // A web UI is either a path on this dashboard or its own host:port.
        function webUrl(web) {
            if (web.path) return web.path;
            return `${web.scheme}://${location.hostname}:${web.port}/`;
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
                    <div class="utility-header">
                        <span class="utility-name">${u.name}</span>
                        <div class="card-actions">
                            ${u.web ? `<a class="open-btn" href="${webUrl(u.web)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Open &#8599;</a>` : ''}
                            <button class="run-btn" onclick="runUtility(event, '${u.name}')">Run Now</button>
                        </div>
                    </div>
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

        async function runUtility(event, name) {
            event.stopPropagation();
            const btn = event.target;
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = 'Running...';

            try {
                const response = await fetch(`/api/run/${name}`, { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    btn.textContent = 'Started!';
                    setTimeout(() => {
                        refresh();
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }, 2000);
                } else {
                    btn.textContent = 'Failed';
                    console.error('Run failed:', data.error);
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }, 2000);
                }
            } catch (error) {
                console.error('Failed to run utility:', error);
                btn.textContent = 'Error';
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.disabled = false;
                }, 2000);
            }
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


@app.route("/contests")
@app.route("/contests/")
def contests_index():
    """List the contest HTML pages, newest first. 'current' always exists."""
    reports = sorted(CONTEST_REPORTS_DIR.glob("*.html"), reverse=True)
    items = ['<li><a href="/contests/current">current</a></li>'] + [
        f'<li><a href="/contests/{r.name}">{r.stem}</a></li>' for r in reports
    ]
    return (
        "<!doctype html><title>Contest reports</title>"
        "<h1>Contest reports</h1><ul>" + "".join(items) + "</ul>"
    )


@app.route("/contests/current")
def contests_current():
    """The newest sweep report; the page shipped in the repo before any sweep."""
    reports = sorted(CONTEST_REPORTS_DIR.glob("*.html"), reverse=True)
    if reports:
        return send_from_directory(str(CONTEST_REPORTS_DIR), reports[0].name)
    return send_from_directory(
        str(CONTEST_SEED_HTML.parent), CONTEST_SEED_HTML.name
    )


@app.route("/contests/<path:filename>")
def contest_report(filename: str):
    """Serve one monthly contest report (send_from_directory blocks traversal)."""
    return send_from_directory(str(CONTEST_REPORTS_DIR), filename)


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


@app.route("/api/run/<utility>", methods=["POST"])
def api_run(utility: str):
    """Manually trigger a utility service to run."""
    # Basic validation - only allow alphanumeric and hyphens
    if not all(c.isalnum() or c == "-" for c in utility):
        return jsonify({"error": "Invalid utility name"}), 400

    # Verify utility is in the enabled list
    enabled = get_enabled_utilities()
    if utility not in enabled:
        return jsonify({"error": "Utility not enabled"}), 400

    service_name = f"{utility}.service"
    try:
        result = subprocess.run(
            ["systemctl", "start", service_name],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return jsonify({"success": True, "message": f"Started {service_name}"})
        else:
            return jsonify({
                "success": False,
                "error": result.stderr.strip() or "Failed to start service",
            }), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def main():
    """Run the Flask development server."""
    port = int(os.environ.get("PORT", 80))
    # Bind to all interfaces so it's accessible on local network
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
