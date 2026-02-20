"""
Supabase Client Singleton
Manages the connection to Supabase using credentials from environment variables.
"""

import os
import threading
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Thread-local storage: each thread gets its own client instance.
# This prevents HTTP/2 connection sharing across threads, which causes
# "Server disconnected" errors when concurrent uploads use asyncio.to_thread.
_thread_local = threading.local()


def get_supabase_client() -> Client:
    """
    Return a Supabase client for the current thread.
    Creates a new instance on first call per thread, then reuses it.
    """
    if not hasattr(_thread_local, "client"):
        _thread_local.client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _thread_local.client


def get_storage_bucket() -> str:
    """
    Get the storage bucket name from environment or use default.
    
    Returns:
        str: Storage bucket name
    """
    return os.getenv("BUCKET_NAME", "videos")


