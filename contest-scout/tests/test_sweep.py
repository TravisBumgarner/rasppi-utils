"""Tests for the contest-scout sweep runner (all subprocess/HTTP mocked)."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import sweep  # noqa: E402


def _proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_commit_and_push_no_changes():
    with patch.object(sweep, "_git", return_value=_proc(stdout="")) as git:
        status = sweep.commit_and_push()
    assert status == "No changes to contest-deadlines.md."
    # Only the porcelain check ran — no commit, no push.
    assert git.call_count == 1


def test_commit_and_push_reports_stranded_commit_on_push_failure():
    def fake_git(*args):
        if args[0] == "status":
            return _proc(stdout=" M social-poster/config/contest-deadlines.md")
        if args[0] == "push":
            return _proc(returncode=1, stderr="auth failed")
        return _proc()

    with patch.object(sweep, "_git", side_effect=fake_git):
        status = sweep.commit_and_push()
    assert "push failed" in status


def test_notify_posts_contact_form_json_and_truncates():
    resp = MagicMock()
    with patch("requests.post", return_value=resp) as post:
        sweep.notify("📸 Time for monthly contests — July 2026", "x" * 5000)
    assert post.call_args.args[0] == sweep.CONTACT_FORM_URL
    sent = post.call_args.kwargs["json"]
    assert sent["subject"] == "📸 Time for monthly contests — July 2026"
    assert len(sent["message"]) == sweep.MESSAGE_LIMIT
    assert sent["name"] == "Contest Scout"
    assert sent["website"] == "rasppi-utils"
    resp.raise_for_status.assert_called_once()


def test_failure_still_notifies():
    with patch.object(sweep, "_git", return_value=_proc()), \
         patch.object(sweep, "run_sweep", side_effect=RuntimeError("boom")), \
         patch("requests.post") as post:
        with pytest.raises(RuntimeError):
            sweep.main()
    sent = post.call_args.kwargs["json"]
    assert "FAILED" in sent["subject"]
    assert "boom" in sent["message"]


def test_run_sweep_raises_on_claude_error(monkeypatch):
    with patch("subprocess.run", return_value=_proc(returncode=2, stderr="bad token")):
        with pytest.raises(RuntimeError, match="bad token"):
            sweep.run_sweep()
