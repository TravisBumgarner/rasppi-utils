#!/usr/bin/env python3
"""Pixels64 - Hosts the Web Bluetooth control UI for the Pixels64 display.

Serves a single static page over HTTPS. HTTPS is required because browsers only
expose the Web Bluetooth API (navigator.bluetooth) in a secure context; plain
http://rasppi-utils.local would make the API unavailable. A self-signed cert is
generated on first run, so the browser shows a one-time "not secure" warning.
"""

import os
import subprocess
from pathlib import Path

from flask import Flask, send_from_directory

app = Flask(__name__)

WEB_DIR = Path(__file__).parent.parent / "web"
CONFIG_DIR = Path("/etc/rasppi-utils/pixels64")
CERT_FILE = CONFIG_DIR / "cert.pem"
KEY_FILE = CONFIG_DIR / "key.pem"
HOSTNAME = "rasppi-utils.local"


def ensure_cert() -> tuple[str, str]:
    """Generate a persistent self-signed cert on first run; reuse it after."""
    if CERT_FILE.exists() and KEY_FILE.exists():
        return str(CERT_FILE), str(KEY_FILE)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(KEY_FILE), "-out", str(CERT_FILE),
            "-days", "3650", "-subj", f"/CN={HOSTNAME}",
            "-addext", f"subjectAltName=DNS:{HOSTNAME},DNS:localhost,IP:127.0.0.1",
        ],
        check=True,
    )
    KEY_FILE.chmod(0o600)
    return str(CERT_FILE), str(KEY_FILE)


@app.route("/")
def index():
    """Serve the Web Bluetooth control UI."""
    return send_from_directory(WEB_DIR, "index.html")


def main():
    port = int(os.environ.get("PORT", 8443))
    cert, key = ensure_cert()
    # Bind to all interfaces so it's reachable on the local network.
    app.run(host="0.0.0.0", port=port, ssl_context=(cert, key))


if __name__ == "__main__":
    main()
