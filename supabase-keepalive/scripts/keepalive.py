#!/usr/bin/env python3
"""Supabase keep-alive script to prevent free-tier project pausing."""

import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_config(env_path: str | None = None) -> dict[str, str]:
    """Load Supabase credentials from environment or .env file.

    Args:
        env_path: Optional path to .env file. If None, uses environment variables.

    Returns:
        Dictionary with 'url', 'key', 'email', and 'password' keys.

    Raises:
        ValueError: If required credentials are missing.
    """
    if env_path:
        load_dotenv(env_path)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    email = os.environ.get("SUPABASE_EMAIL")
    password = os.environ.get("SUPABASE_PASSWORD")

    if not url:
        raise ValueError("SUPABASE_URL is not set")
    if not key:
        raise ValueError("SUPABASE_KEY is not set")
    if not email:
        raise ValueError("SUPABASE_EMAIL is not set")
    if not password:
        raise ValueError("SUPABASE_PASSWORD is not set")

    return {"url": url, "key": key, "email": email, "password": password}


def ping_supabase(url: str, key: str, email: str, password: str) -> bool:
    """Connect to Supabase and sign in to generate activity.

    Args:
        url: Supabase project URL.
        key: Supabase API key.
        email: User email for authentication.
        password: User password for authentication.

    Returns:
        True if ping was successful, False otherwise.
    """
    try:
        client = create_client(url, key)
        client.auth.sign_in_with_password({"email": email, "password": password})
        return True
    except Exception as e:
        logger.error(f"Failed to ping Supabase: {e}")
        return False


def main(env_path: str | None = None) -> int:
    """Main entry point for the keep-alive script.

    Args:
        env_path: Optional path to .env file.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    try:
        config = load_config(env_path)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    timestamp = datetime.now().isoformat()

    if ping_supabase(config["url"], config["key"], config["email"], config["password"]):
        logger.info(f"[{timestamp}] Supabase keep-alive ping successful")
        return 0
    else:
        logger.error(f"[{timestamp}] Supabase keep-alive ping failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
