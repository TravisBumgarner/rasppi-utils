# Contest Scout

Monthly photo-contest sweep, run on the Pi. A systemd timer runs Claude Code
headless with this repo's `/find-contests` skill
([.claude/skills/find-contests](../.claude/skills/find-contests/SKILL.md)),
which researches contest deadlines/eligibility/rights on official pages and
updates the live deadlines file at
`/var/lib/rasppi-utils/contest-scout/contest-deadlines.md` — deliberately
**not version controlled**; it's seeded once from the repo's
[social-poster/config/contest-deadlines.md](../social-poster/config/contest-deadlines.md)
and lives on the Pi from then on. The summary is sent as a JSON POST through
the same **contact-form relay** the portfolio sites use
(`contact-form.nfshost.com`), subject "📸 Time for monthly contests" — the
nudge to go review them. Failures notify too (subject says FAILED), so
silence always means "the timer didn't fire," never "it broke quietly."

## Setup

`sudo ./bootstrap-pi.sh` (idempotent, run from the repo root) handles the
machine side when `contest-scout` is enabled in
[utilities.conf](../utilities.conf): installs Node + the Claude Code CLI,
allowlists the repo for root git (the sweep does a read-only `git pull`;
it never commits or pushes), installs the service + timer via `sync.sh`,
and warns about any placeholder credentials left in the `.env`.

One credential comes from an external login, so it stays manual — paste it
into `/etc/rasppi-utils/contest-scout/.env`:

- **Claude token** — on any machine where you're logged in to Claude, run
  `claude setup-token` and set `CLAUDE_CODE_OAUTH_TOKEN` (uses your
  subscription; alternatively set `ANTHROPIC_API_KEY` for API billing).

Notifications need no credentials — the contact-form relay is a public
endpoint (override with `CONTACT_FORM_URL` if it ever moves).

## Operating

```sh
sudo systemctl start contest-scout.service   # run a sweep right now
journalctl -u contest-scout -n 100           # logs from the last run
systemctl list-timers contest-scout.timer    # next scheduled run
```

Schedule: 1st of each month, ~09:00 (`Persistent=true` catches a Pi that
was off). Claude runs with a read/edit/web-research tool allowlist only.
Read the current list any time with:

```sh
cat /var/lib/rasppi-utils/contest-scout/contest-deadlines.md
```
