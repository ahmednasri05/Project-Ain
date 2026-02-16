"""
Database Package
Supabase integration for Instagram reels and comments.
"""

from .supabase_client import get_supabase_client, get_storage_bucket
from .instagram_db import (
    save_reel,
    get_reel_by_shortcode,
    save_comment_thread,
    verify_reel_exists,
    bulk_save_comments
)
from .storage_utils import (
    download_video_stream,
    upload_to_supabase,
    download_and_upload_reel,
    get_public_url,
    delete_from_storage
)

__all__ = [
    # Client
    "get_supabase_client",
    "get_storage_bucket",
    # Instagram DB
    "save_reel",
    "get_reel_by_shortcode",
    "save_comment_thread",
    "verify_reel_exists",
    "bulk_save_comments",
    # Storage
    "download_video_stream",
    "upload_to_supabase",
    "download_and_upload_reel",
    "get_public_url",
    "delete_from_storage",
]

