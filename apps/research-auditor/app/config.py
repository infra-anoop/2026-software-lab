"""Centralized env loading and validation for CLI/HTTP entrypoints."""
import os
import sys

from dotenv import load_dotenv


def init_env() -> None:
    """Load .env from the project root. Call early in CLI/HTTP entrypoints."""
    load_dotenv()


def require_openai_api_key() -> None:
    """Exit with error message if OPENAI_API_KEY is not set. Call before using agents."""
    key = os.getenv("OPENAI_API_KEY")
    if not key or not key.strip():
        print("❌ ERROR: OPENAI_API_KEY not found in environment variables.")
        sys.exit(1)
