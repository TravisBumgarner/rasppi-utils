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

## One-time Pi setup

1. **Claude Code CLI** on the Pi:

   ```sh
   npm install -g @anthropic-ai/claude-code
   which claude   # if not /usr/local/bin, set CLAUDE_BIN in the .env
   ```

2. **Credentials** — on any machine where you're logged in to Claude, run
   `claude setup-token` and paste the token into the `.env` when `sync.sh`
   prompts (uses your subscription; alternatively set `ANTHROPIC_API_KEY`
   for API billing).

3. **Pushover** — create an application at <https://pushover.net/apps/build>
   (app token) and grab your user key from the dashboard.

4. **Git push auth** — the sweep commits to the Pi's clone and pushes. The
   default clone is HTTPS, so either store a GitHub PAT
   (`git config credential.helper store` + one manual push) or switch the
   remote to SSH with a deploy key. If push auth is missing the run still
   works; the notification will say the commit is stranded on the Pi.

5. Enable it: `contest-scout` in [utilities.conf](../utilities.conf), then
   `sudo ./sync.sh` (prompts for the `.env`, installs the service + timer).

## Operating

```sh
sudo systemctl start contest-scout.service   # run a sweep right now
journalctl -u contest-scout -n 100           # logs from the last run
systemctl list-timers contest-scout.timer    # next scheduled run
```

Schedule: 1st of each month, ~09:00 (`Persistent=true` catches a Pi that was
off). Claude runs with a read/edit/web-research tool allowlist only — the
commit/push is done by [scripts/sweep.py](scripts/sweep.py), not by Claude.
