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


def _use_tmp_data_dir(tmp_path, monkeypatch, seed="seeded contest list\n"):
    """Point the module at a throwaway DATA_DIR and repo-seed file."""
    seed_path = tmp_path / "repo-copy.md"
    seed_path.write_text(seed)
    data_dir = tmp_path / "data"
    monkeypatch.setattr(sweep, "SEED_PATH", seed_path)
    monkeypatch.setattr(sweep, "DATA_DIR", data_dir)
    monkeypatch.setattr(sweep, "DEADLINES_PATH", data_dir / "contest-deadlines.md")


def test_ensure_deadlines_file_seeds_from_repo_copy(tmp_path, monkeypatch):
    _use_tmp_data_dir(tmp_path, monkeypatch)
    sweep.ensure_deadlines_file()
    assert sweep.DEADLINES_PATH.read_text() == "seeded contest list\n"


def test_ensure_deadlines_file_never_overwrites(tmp_path, monkeypatch):
    _use_tmp_data_dir(tmp_path, monkeypatch)
    sweep.ensure_deadlines_file()
    sweep.DEADLINES_PATH.write_text("live edits from a previous sweep")
    sweep.ensure_deadlines_file()
    assert sweep.DEADLINES_PATH.read_text() == "live edits from a previous sweep"


def test_prompt_names_the_data_dir_file(tmp_path, monkeypatch):
    _use_tmp_data_dir(tmp_path, monkeypatch)
    assert str(sweep.DEADLINES_PATH) in sweep._prompt()


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


def test_main_reports_updated_file(tmp_path, monkeypatch):
    _use_tmp_data_dir(tmp_path, monkeypatch)

    def fake_sweep():
        sweep.DEADLINES_PATH.write_text("new contests found")
        return "Sony WPA is open."

    with patch.object(sweep, "run_sweep", side_effect=fake_sweep), \
         patch("subprocess.run", return_value=_proc()), \
         patch("requests.post") as post:
        sweep.main()
    sent = post.call_args.kwargs["json"]
    assert "Sony WPA is open." in sent["message"]
    assert "Updated" in sent["message"]


def test_main_reports_no_changes(tmp_path, monkeypatch):
    _use_tmp_data_dir(tmp_path, monkeypatch)
    with patch.object(sweep, "run_sweep", return_value="Nothing new."), \
         patch("subprocess.run", return_value=_proc()), \
         patch("requests.post") as post:
        sweep.main()
    assert "No changes" in post.call_args.kwargs["json"]["message"]


def test_failure_still_notifies(tmp_path, monkeypatch):
    _use_tmp_data_dir(tmp_path, monkeypatch)
    with patch.object(sweep, "run_sweep", side_effect=RuntimeError("boom")), \
         patch("subprocess.run", return_value=_proc()), \
         patch("requests.post") as post:
        with pytest.raises(RuntimeError):
            sweep.main()
    sent = post.call_args.kwargs["json"]
    assert "FAILED" in sent["subject"]
    assert "boom" in sent["message"]


def test_run_sweep_raises_on_claude_error():
    with patch("subprocess.run", return_value=_proc(returncode=2, stderr="bad token")):
        with pytest.raises(RuntimeError, match="bad token"):
            sweep.run_sweep()
