#!/usr/bin/env python3
"""Contest Scout - monthly photo-contest sweep, run on the Pi.

Runs Claude Code headless with the repo's /find-contests skill, which
verifies contest deadlines/eligibility/rights on official pages and updates
the live deadlines file. That file lives in the Pi's DATA_DIR (not the git
repo — deliberately unversioned), seeded once from the repo's copy at
social-poster/config/contest-deadlines.md. The summary is then sent through
the same contact-form relay the portfolio sites use — the nudge that it's
time to review the month's contests.

Every outcome notifies — including failures — so a silent month always
means "the timer didn't fire," never "it broke quietly."

Triggered by contest-scout.timer (monthly). Credentials come from
/etc/rasppi-utils/contest-scout/.env (see config/.env.example).
"""

import hashlib
import os
import subprocess
from datetime import date
from pathlib import Path

import requests

# contest-scout/scripts/sweep.py -> <repo>
REPO_ROOT = Path(__file__).resolve().parents[2]

# DATA_DIR is set by systemd in prod (/var/lib/rasppi-utils/contest-scout);
# the default is a dev-friendly location inside the utility.
DATA_DIR = Path(
    os.environ.get("DATA_DIR", Path(__file__).resolve().parents[1] / "data")
)
DEADLINES_PATH = DATA_DIR / "contest-deadlines.md"

# The repo copy only seeds the data dir on first run; after that the data-dir
# file is the source of truth and is never committed.
SEED_PATH = REPO_ROOT / "social-poster" / "config" / "contest-deadlines.md"

# Same relay the portfolio contact forms POST to (see
# Engineering-Portfolio-and-Blog frontend/src/sharedComponents/ContactForm.tsx).
CONTACT_FORM_URL = os.environ.get(
    "CONTACT_FORM_URL", "https://contact-form.nfshost.com/contact"
)
# The contact forms cap messages at 800 chars client-side; match it.
MESSAGE_LIMIT = 800

# Headless permission allowlist: web research + editing the deadlines file.
ALLOWED_TOOLS = "WebSearch,WebFetch,Read,Glob,Grep,Edit,Write"

CLAUDE_TIMEOUT_SECONDS = 45 * 60


def _prompt() -> str:
    """The headless instruction; the final reply becomes the notification."""
    return (
        f"Run /find-contests, but the deadlines file to read and update is "
        f"{DEADLINES_PATH} — NOT the repo copy. After updating it, reply "
        "with ONLY a short push-notification summary (max 600 characters, "
        "plain text, no markdown): what's newly open, what closes within 6 "
        "weeks, and anything newly rejected. If nothing changed, say so in "
        "one sentence."
    )


def ensure_deadlines_file() -> None:
    """Create DATA_DIR and seed the deadlines file from the repo copy once."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DEADLINES_PATH.exists():
        DEADLINES_PATH.write_text(SEED_PATH.read_text(encoding="utf-8"),
                                  encoding="utf-8")


def _file_hash() -> str:
    return hashlib.sha256(DEADLINES_PATH.read_bytes()).hexdigest()


def run_sweep() -> str:
    """Run the headless Claude sweep; return its final reply text."""
    claude_bin = os.environ.get("CLAUDE_BIN", "claude")
    result = subprocess.run(
        [
            claude_bin, "-p", _prompt(),
            "--allowedTools", ALLOWED_TOOLS,
            # The deadlines file lives outside the repo checkout.
            "--add-dir", str(DATA_DIR),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True,
        timeout=CLAUDE_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude exited {result.returncode}: "
            f"{(result.stderr or result.stdout)[:400]}"
        )
    return result.stdout.strip()


def notify(subject: str, message: str) -> None:
    """Send the summary through the contact-form relay (JSON POST)."""
    resp = requests.post(
        CONTACT_FORM_URL,
        json={
            "name": "Contest Scout",
            "email": "",
            "subject": subject,
            "message": message[:MESSAGE_LIMIT],
            "website": "rasppi-utils",
        },
        timeout=30,
    )
    resp.raise_for_status()


def main() -> None:
    month = f"{date.today():%B %Y}"
    try:
        # Best-effort refresh of the checkout (skill/source-list updates);
        # read-only, needs no git credentials.
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "pull", "--ff-only"],
            capture_output=True, text=True, check=False,
        )
        ensure_deadlines_file()
        before = _file_hash()
        summary = run_sweep()
        changed = _file_hash() != before
    except Exception as exc:  # noqa: BLE001 - failure must still notify.
        notify(
            f"Contest sweep FAILED — {month}",
            f"{type(exc).__name__}: {str(exc)[:500]}\n"
            "Check: journalctl -u contest-scout",
        )
        raise

    status = (
        f"Updated {DEADLINES_PATH}." if changed
        else "No changes to the deadlines file."
    )
    notify(
        f"📸 Time for monthly contests — {month}",
        f"{summary}\n\n{status}",
    )
    print(f"contest-scout: done. {status}")


if __name__ == "__main__":
    main()
