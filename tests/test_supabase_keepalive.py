"""Tests for the Supabase keep-alive script."""

import os
from unittest.mock import MagicMock, patch

import pytest

from scripts.supabase_keepalive import load_config, main, ping_supabase


class TestLoadConfig:
    """Tests for loading configuration from environment or .env file."""

    def test_loads_credentials_from_environment_variables(self):
        """Should load SUPABASE_URL and SUPABASE_KEY from environment."""
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-key-123",
            },
        ):
            config = load_config()

        assert config["url"] == "https://test.supabase.co"
        assert config["key"] == "test-key-123"

    def test_loads_credentials_from_env_file(self, tmp_path):
        """Should load credentials from a .env file when path is provided."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "SUPABASE_URL=https://file.supabase.co\nSUPABASE_KEY=file-key-456\n"
        )

        config = load_config(str(env_file))

        assert config["url"] == "https://file.supabase.co"
        assert config["key"] == "file-key-456"

    def test_raises_error_when_url_missing(self):
        """Should raise ValueError when SUPABASE_URL is not set."""
        with patch.dict(os.environ, {"SUPABASE_KEY": "key"}, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_URL"):
                load_config()

    def test_raises_error_when_key_missing(self):
        """Should raise ValueError when SUPABASE_KEY is not set."""
        with patch.dict(
            os.environ, {"SUPABASE_URL": "https://test.supabase.co"}, clear=True
        ):
            with pytest.raises(ValueError, match="SUPABASE_KEY"):
                load_config()


class TestPingSupabase:
    """Tests for the Supabase ping functionality."""

    def test_returns_true_on_successful_query(self):
        """Should return True when Supabase query succeeds."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[{"id": 1}])
        )

        with patch(
            "scripts.supabase_keepalive.create_client", return_value=mock_client
        ):
            result = ping_supabase("https://test.supabase.co", "test-key")

        assert result is True

    def test_returns_false_on_connection_error(self):
        """Should return False when Supabase connection fails."""
        with patch(
            "scripts.supabase_keepalive.create_client",
            side_effect=Exception("Connection failed"),
        ):
            result = ping_supabase("https://test.supabase.co", "test-key")

        assert result is False

    def test_returns_false_on_query_error(self):
        """Should return False when query execution fails."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception(
            "Query failed"
        )

        with patch(
            "scripts.supabase_keepalive.create_client", return_value=mock_client
        ):
            result = ping_supabase("https://test.supabase.co", "test-key")

        assert result is False


class TestMain:
    """Tests for the main entry point."""

    def test_returns_zero_on_success(self):
        """Should return exit code 0 when ping succeeds."""
        with (
            patch(
                "scripts.supabase_keepalive.load_config",
                return_value={"url": "https://test.supabase.co", "key": "test-key"},
            ),
            patch("scripts.supabase_keepalive.ping_supabase", return_value=True),
        ):
            result = main()

        assert result == 0

    def test_returns_one_on_ping_failure(self):
        """Should return exit code 1 when ping fails."""
        with (
            patch(
                "scripts.supabase_keepalive.load_config",
                return_value={"url": "https://test.supabase.co", "key": "test-key"},
            ),
            patch("scripts.supabase_keepalive.ping_supabase", return_value=False),
        ):
            result = main()

        assert result == 1

    def test_returns_one_on_config_error(self):
        """Should return exit code 1 when config loading fails."""
        with patch(
            "scripts.supabase_keepalive.load_config",
            side_effect=ValueError("Missing credentials"),
        ):
            result = main()

        assert result == 1

    def test_passes_env_path_to_load_config(self, tmp_path):
        """Should pass env_path argument to load_config."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "SUPABASE_URL=https://test.supabase.co\nSUPABASE_KEY=test-key\n"
        )

        with (
            patch("scripts.supabase_keepalive.load_config") as mock_load,
            patch("scripts.supabase_keepalive.ping_supabase", return_value=True),
        ):
            mock_load.return_value = {
                "url": "https://test.supabase.co",
                "key": "test-key",
            }
            main(str(env_file))

        mock_load.assert_called_once_with(str(env_file))
