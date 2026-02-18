"""Shared Supabase client. Single place that reads env and creates the client."""
import os
from supabase import create_client, Client

_cached: Client | None = None
_initialized = False


def get_supabase_client() -> Client | None:
    """Return a cached Supabase client if SUPABASE_URL and SUPABASE_SECRET_KEY are set; else None."""
    global _cached, _initialized
    if not _initialized:
        _initialized = True
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SECRET_KEY")
        if not url or not key or not url.strip() or not key.strip():
            print("Supabase disabled: missing SUPABASE_URL or SUPABASE_SECRET_KEY")
            _cached = None
        else:
            try:
                _cached = create_client(url, key)
            except Exception as e:
                print("Supabase disabled: invalid SUPABASE_URL or SUPABASE_SECRET_KEY")
                print(f"Supabase error: {type(e).__name__}: {e}")
                _cached = None
    return _cached
