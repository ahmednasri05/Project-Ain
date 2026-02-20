"""
Database Package
Supabase integration for Instagram reels and comments.
"""

from .client import get_supabase_client, get_storage_bucket
from .crud import (
    save_reel,
    get_reel_by_shortcode,
    increment_mention_count,
    save_comment_thread,
    verify_reel_exists,
    bulk_save_comments,
    insert_pipeline_run,
    update_pipeline_run,
    insert_failed_request,
    fetch_comments_from_db,
)
from .storage_utils import (
    upload_to_supabase,
    upload_large_file,
    get_public_url,
    delete_from_storage,
)

__all__ = [
    # Client
    "get_supabase_client",
    "get_storage_bucket",
    # Instagram DB
    "save_reel",
    "get_reel_by_shortcode",
    "increment_mention_count",
    "save_comment_thread",
    "verify_reel_exists",
    "bulk_save_comments",
    # Pipeline runs
    "insert_pipeline_run",
    "update_pipeline_run",
    "insert_failed_request",
    "fetch_comments_from_db",
    # Storage
    "upload_to_supabase",
    "upload_large_file",
    "get_public_url",
    "delete_from_storage",
]

