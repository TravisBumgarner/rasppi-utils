# Contest Scout

Monthly photo-contest sweep, run on the Pi. A systemd timer runs Claude Code
headless with this repo's `/find-contests` skill
([.claude/skills/find-contests](../.claude/skills/find-contests/SKILL.md)),
which researches contest deadlines/eligibility/rights on official pages and
updates [social-poster/config/contest-deadlines.md](../social-poster/config/contest-deadlines.md).
Changes are committed and pushed, and a **Pushover** notification lands on
your phone with the summary — the nudge that it's time to review the month's
contests. Failures notify too (high priority), so silence always means "the
timer didn't fire," never "it broke quietly."

## Setup

`sudo ./bootstrap-pi.sh` (idempotent, run from the repo root) handles the
machine side when `contest-scout` is enabled in
[utilities.conf](../utilities.conf): installs Node + the Claude Code CLI,
allowlists the repo for root git, prompts once for a GitHub PAT if pushing
isn't authorized, installs the service + timer via `sync.sh`, and warns
about any placeholder credentials left in the `.env`.

Two credentials come from external accounts, so they stay manual — paste
them into `/etc/rasppi-utils/contest-scout/.env`:

1. **Claude token** — on any machine where you're logged in to Claude, run
   `claude setup-token` and set `CLAUDE_CODE_OAUTH_TOKEN` (uses your
   subscription; alternatively set `ANTHROPIC_API_KEY` for API billing).
2. **Pushover** — create an application at <https://pushover.net/apps/build>
   (`PUSHOVER_APP_TOKEN`) and grab your user key from the dashboard
   (`PUSHOVER_USER_KEY`).

If push auth is ever missing, runs still work — the notification will say
the commit is stranded on the Pi's clone.

## Operating

```sh
sudo systemctl start contest-scout.service   # run a sweep right now
journalctl -u contest-scout -n 100           # logs from the last run
systemctl list-timers contest-scout.timer    # next scheduled run
```

Schedule: 1st of each month, ~09:00 (`Persistent=true` catches a Pi that was
off). Claude runs with a read/edit/web-research tool allowlist only — the
commit/push is done by [scripts/sweep.py](scripts/sweep.py), not by Claude.
