#!/usr/bin/env python3
"""Contest Scout - monthly photo-contest sweep, run on the Pi.

Runs Claude Code headless with the repo's /find-contests skill, which
verifies contest deadlines/eligibility/rights on official pages and updates
social-poster/config/contest-deadlines.md. If the file changed, commits and
pushes, then sends Claude's summary through the same contact-form service
the portfolio sites use (contact-form.nfshost.com) — the nudge that it's
time to review the month's contests.

Every outcome notifies — including failures — so a silent month always
means "the timer didn't fire," never "it broke quietly."

Triggered by contest-scout.timer (monthly). Credentials come from
/etc/rasppi-utils/contest-scout/.env (see config/.env.example).
"""

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import requests

# contest-scout/scripts/sweep.py -> <repo>
REPO_ROOT = Path(__file__).resolve().parents[2]
DEADLINES_FILE = "social-poster/config/contest-deadlines.md"

# Same relay the portfolio contact forms POST to (see
# Engineering-Portfolio-and-Blog frontend/src/sharedComponents/ContactForm.tsx).
CONTACT_FORM_URL = os.environ.get(
    "CONTACT_FORM_URL", "https://contact-form.nfshost.com/contact"
)
# The contact forms cap messages at 800 chars client-side; match it.
MESSAGE_LIMIT = 800

# The skill does the real work; the final reply becomes the notification.
PROMPT = (
    "Run /find-contests. After updating the deadlines file, reply with ONLY "
    "a short push-notification summary (max 600 characters, plain text, no "
    "markdown): what's newly open, what closes within 6 weeks, and anything "
    "newly rejected. If nothing changed, say so in one sentence."
)

# Headless permission allowlist: web research + editing the deadlines doc.
# Committing is done by this script, not by Claude.
ALLOWED_TOOLS = "WebSearch,WebFetch,Read,Glob,Grep,Edit,Write"

CLAUDE_TIMEOUT_SECONDS = 45 * 60


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True, text=True, check=False,
    )


def run_sweep() -> str:
    """Run the headless Claude sweep; return its final reply text."""
    claude_bin = os.environ.get("CLAUDE_BIN", "claude")
    result = subprocess.run(
        [
            claude_bin, "-p", PROMPT,
            "--allowedTools", ALLOWED_TOOLS,
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


def commit_and_push() -> str:
    """Commit the updated deadlines file if it changed; try to push.

    Returns a one-line status for the notification. Push failures are
    reported, not fatal — the sweep result still lives on the Pi's clone.
    """
    changed = _git("status", "--porcelain", "--", DEADLINES_FILE).stdout.strip()
    if not changed:
        return "No changes to contest-deadlines.md."

    _git("add", DEADLINES_FILE)
    commit = _git(
        "commit",
        "-m", f"contest-scout: monthly sweep {date.today():%Y-%m}",
        "-m", "Automated run of /find-contests on the Pi.",
    )
    if commit.returncode != 0:
        return f"Commit failed: {commit.stderr.strip()[:200]}"

    push = _git("push")
    if push.returncode != 0:
        return "Committed on the Pi but push failed — pull from the Pi or fix git auth."
    return "Updated contest-deadlines.md (committed & pushed)."


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
        # Start from the freshest main so the sweep edits current data.
        _git("pull", "--ff-only")
        summary = run_sweep()
        git_status = commit_and_push()
    except Exception as exc:  # noqa: BLE001 - failure must still notify.
        notify(
            f"Contest sweep FAILED — {month}",
            f"{type(exc).__name__}: {str(exc)[:500]}\n"
            "Check: journalctl -u contest-scout",
        )
        raise

    notify(
        f"📸 Time for monthly contests — {month}",
        f"{summary}\n\n{git_status}\n"
        "Full list: social-poster/config/contest-deadlines.md",
    )
    print(f"contest-scout: done. {git_status}")


if __name__ == "__main__":
    main()
