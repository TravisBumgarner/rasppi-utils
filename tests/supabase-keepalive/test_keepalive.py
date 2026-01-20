"""Tests for the Supabase keep-alive script."""

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load the keepalive module from the hyphenated directory
_module_path = Path(__file__).parent.parent.parent / "supabase-keepalive" / "scripts" / "keepalive.py"
_spec = importlib.util.spec_from_file_location("keepalive", _module_path)
keepalive = importlib.util.module_from_spec(_spec)
sys.modules["keepalive"] = keepalive
_spec.loader.exec_module(keepalive)

load_config = keepalive.load_config
main = keepalive.main
ping_supabase = keepalive.ping_supabase


class TestLoadConfig:
    """Tests for loading configuration from environment or .env file."""

    def test_loads_credentials_from_environment_variables(self):
        """Should load all credentials from environment."""
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-key-123",
                "SUPABASE_EMAIL": "test@example.com",
                "SUPABASE_PASSWORD": "test-password",
            },
        ):
            config = load_config()

        assert config["url"] == "https://test.supabase.co"
        assert config["key"] == "test-key-123"
        assert config["email"] == "test@example.com"
        assert config["password"] == "test-password"

    def test_loads_credentials_from_env_file(self, tmp_path):
        """Should load credentials from a .env file when path is provided."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "SUPABASE_URL=https://file.supabase.co\n"
            "SUPABASE_KEY=file-key-456\n"
            "SUPABASE_EMAIL=file@example.com\n"
            "SUPABASE_PASSWORD=file-password\n"
        )

        config = load_config(str(env_file))

        assert config["url"] == "https://file.supabase.co"
        assert config["key"] == "file-key-456"
        assert config["email"] == "file@example.com"
        assert config["password"] == "file-password"

    def test_raises_error_when_url_missing(self):
        """Should raise ValueError when SUPABASE_URL is not set."""
        with patch.dict(os.environ, {
            "SUPABASE_KEY": "key",
            "SUPABASE_EMAIL": "test@example.com",
            "SUPABASE_PASSWORD": "password",
        }, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_URL"):
                load_config()

    def test_raises_error_when_key_missing(self):
        """Should raise ValueError when SUPABASE_KEY is not set."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_EMAIL": "test@example.com",
            "SUPABASE_PASSWORD": "password",
        }, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_KEY"):
                load_config()

    def test_raises_error_when_email_missing(self):
        """Should raise ValueError when SUPABASE_EMAIL is not set."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "key",
            "SUPABASE_PASSWORD": "password",
        }, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_EMAIL"):
                load_config()

    def test_raises_error_when_password_missing(self):
        """Should raise ValueError when SUPABASE_PASSWORD is not set."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "key",
            "SUPABASE_EMAIL": "test@example.com",
        }, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_PASSWORD"):
                load_config()


class TestPingSupabase:
    """Tests for the Supabase ping functionality."""

    def test_returns_true_on_successful_sign_in(self):
        """Should return True when Supabase sign-in succeeds."""
        mock_client = MagicMock()

        with patch(
            "keepalive.create_client", return_value=mock_client
        ):
            result = ping_supabase(
                "https://test.supabase.co", "test-key",
                "test@example.com", "password"
            )

        assert result is True
        mock_client.auth.sign_in_with_password.assert_called_once_with({
            "email": "test@example.com",
            "password": "password",
        })

    def test_returns_false_on_connection_error(self):
        """Should return False when Supabase connection fails."""
        with patch(
            "keepalive.create_client",
            side_effect=Exception("Connection failed"),
        ):
            result = ping_supabase(
                "https://test.supabase.co", "test-key",
                "test@example.com", "password"
            )

        assert result is False

    def test_returns_false_on_auth_error(self):
        """Should return False when authentication fails."""
        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.side_effect = Exception(
            "Invalid credentials"
        )

        with patch(
            "keepalive.create_client", return_value=mock_client
        ):
            result = ping_supabase(
                "https://test.supabase.co", "test-key",
                "test@example.com", "password"
            )

        assert result is False


class TestMain:
    """Tests for the main entry point."""

    def test_returns_zero_on_success(self):
        """Should return exit code 0 when ping succeeds."""
        with (
            patch(
                "keepalive.load_config",
                return_value={
                    "url": "https://test.supabase.co",
                    "key": "test-key",
                    "email": "test@example.com",
                    "password": "password",
                },
            ),
            patch("keepalive.ping_supabase", return_value=True),
        ):
            result = main()

        assert result == 0

    def test_returns_one_on_ping_failure(self):
        """Should return exit code 1 when ping fails."""
        with (
            patch(
                "keepalive.load_config",
                return_value={
                    "url": "https://test.supabase.co",
                    "key": "test-key",
                    "email": "test@example.com",
                    "password": "password",
                },
            ),
            patch("keepalive.ping_supabase", return_value=False),
        ):
            result = main()

        assert result == 1

    def test_returns_one_on_config_error(self):
        """Should return exit code 1 when config loading fails."""
        with patch(
            "keepalive.load_config",
            side_effect=ValueError("Missing credentials"),
        ):
            result = main()

        assert result == 1

    def test_passes_env_path_to_load_config(self, tmp_path):
        """Should pass env_path argument to load_config."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "SUPABASE_URL=https://test.supabase.co\n"
            "SUPABASE_KEY=test-key\n"
            "SUPABASE_EMAIL=test@example.com\n"
            "SUPABASE_PASSWORD=password\n"
        )

        with (
            patch("keepalive.load_config") as mock_load,
            patch("keepalive.ping_supabase", return_value=True),
        ):
            mock_load.return_value = {
                "url": "https://test.supabase.co",
                "key": "test-key",
                "email": "test@example.com",
                "password": "password",
            }
            main(str(env_file))

        mock_load.assert_called_once_with(str(env_file))
