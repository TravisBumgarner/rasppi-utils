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
        Dictionary with 'url' and 'key' keys.

    Raises:
        ValueError: If required credentials are missing.
    """
    if env_path:
        load_dotenv(env_path)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url:
        raise ValueError("SUPABASE_URL is not set")
    if not key:
        raise ValueError("SUPABASE_KEY is not set")

    return {"url": url, "key": key}


def ping_supabase(url: str, key: str) -> bool:
    """Connect to Supabase and execute a simple query.

    Args:
        url: Supabase project URL.
        key: Supabase API key.

    Returns:
        True if ping was successful, False otherwise.
    """
    try:
        client = create_client(url, key)
        # Execute a simple query to generate activity
        # Using a generic table query that will work even if table doesn't exist
        # The goal is just to make a request to the database
        client.table("_keepalive").select("*").limit(1).execute()
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

    if ping_supabase(config["url"], config["key"]):
        logger.info(f"[{timestamp}] Supabase keep-alive ping successful")
        return 0
    else:
        logger.error(f"[{timestamp}] Supabase keep-alive ping failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
