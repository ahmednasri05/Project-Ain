"""
Instagram Database Utilities
Async functions for inserting Instagram reels and comments into Supabase.
Includes thin CRUD for pipeline_runs and failed_requests tables.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from .client import get_supabase_client


async def get_reel_by_shortcode(shortcode: str) -> Optional[Dict[str, Any]]:
    """
    Fetch an existing reel by shortcode.
    
    Args:
        shortcode: Instagram shortcode (e.g., "DRLS0KOAdv2")
        
    Returns:
        Dict or None: Reel record if found, None otherwise
    """
    def _fetch():
        supabase = get_supabase_client()
        response = supabase.table("raw_instagram_reels").select("*").eq("shortcode", shortcode).execute()
        return response.data[0] if response.data else None
    
    return await asyncio.to_thread(_fetch)


async def save_reel(
    reel_json: Dict[str, Any],
    storage_path: Optional[str] = None,
    audio_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Insert or update an Instagram reel in the database.

    Args:
        reel_json: Instagram post JSON payload
        storage_path: Video path in Supabase Storage (optional)
        audio_path: Audio path in Supabase Storage (optional)

    Returns:
        Dict: Inserted/updated database record

    Example:
        reel_record = await save_reel(
            reel_json,
            storage_path="videos/DRLS0KOAdv2.mp4",
            audio_path="audio/DRLS0KOAdv2.mp3",
        )
    """
    def _insert():
        supabase = get_supabase_client()
        
        # Build stats JSONB
        stats = {
            "video_view_count": reel_json.get("videoViewCount"),
            "video_play_count": reel_json.get("videoPlayCount"),
            "likes_count": reel_json.get("likesCount"),
            "comments_count": reel_json.get("commentsCount"),
            "video_duration": reel_json.get("videoDuration"),
        }
        
        # Prepare data
        reel_data = {
            "instagram_id": reel_json["id"],
            "shortcode": reel_json["shortCode"],
            "caption": reel_json.get("caption"),
            "owner_id": reel_json.get("ownerId"),
            "owner_username": reel_json.get("ownerUsername"),
            "posted_at": reel_json.get("timestamp"),
            "stats": stats,
            "storage_bucket_path": storage_path,
            "storage_audio_path": audio_path,
        }
        
        # Upsert (insert or update if exists)
        response = supabase.table("raw_instagram_reels").upsert(
            reel_data,
            on_conflict="instagram_id"
        ).execute()
        
        return response.data[0] if response.data else None
    
    return await asyncio.to_thread(_insert)


async def increment_mention_count(shortcode: str) -> None:
    """
    Atomically increment mention_count on a reel record.
    Called when the same shortcode is re-submitted (step 0) or when a
    fingerprint-matched repost is detected (step 4).

    Args:
        shortcode: Shortcode of the original reel to increment
    """
    def _increment():
        supabase = get_supabase_client()
        supabase.rpc("increment_reel_mention_count", {"reel_shortcode": shortcode}).execute()

    return await asyncio.to_thread(_increment)


async def save_comment_thread(
    comment_json: Dict[str, Any],
    reel_shortcode: str,
    source_shortcode: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Insert a comment and all its nested replies.

    Args:
        comment_json: Comment JSON with potential nested "replies" array
        reel_shortcode: Shortcode of the incident reel (FK, used for grouping)
        source_shortcode: Shortcode where the comment physically appeared.
                          Defaults to reel_shortcode (i.e. original, non-repost).

    Returns:
        List[Dict]: List of inserted comment records

    Example:
        # Original reel — source equals reel
        await save_comment_thread(comment_json, "ABC")

        # Repost — comments attributed to original incident but sourced from repost
        await save_comment_thread(comment_json, "ABC", source_shortcode="XYZ")
    """
    resolved_source = source_shortcode or reel_shortcode

    def _insert_thread():
        supabase = get_supabase_client()
        inserted_records = []

        parent_data = {
            "instagram_comment_id": comment_json["id"],
            "reel_shortcode": reel_shortcode,
            "source_shortcode": resolved_source,
            "text_content": comment_json.get("text", ""),
            "owner_username": comment_json.get("ownerUsername"),
            "like_count": comment_json.get("likesCount", 0),
            "posted_at": comment_json.get("timestamp"),
            "parent_comment_id": None,
        }

        try:
            parent_response = supabase.table("instagram_comments").upsert(
                parent_data,
                on_conflict="instagram_comment_id"
            ).execute()

            if parent_response.data:
                parent_record = parent_response.data[0]
                inserted_records.append(parent_record)
                db_parent_id = parent_record["id"]

                if "replies" in comment_json and comment_json["replies"]:
                    replies_data = [
                        {
                            "instagram_comment_id": reply["id"],
                            "reel_shortcode": reel_shortcode,
                            "source_shortcode": resolved_source,
                            "text_content": reply.get("text", ""),
                            "owner_username": reply.get("ownerUsername"),
                            "like_count": reply.get("likesCount", 0),
                            "posted_at": reply.get("timestamp"),
                            "parent_comment_id": db_parent_id,
                        }
                        for reply in comment_json["replies"]
                    ]

                    if replies_data:
                        replies_response = supabase.table("instagram_comments").upsert(
                            replies_data,
                            on_conflict="instagram_comment_id"
                        ).execute()

                        if replies_response.data:
                            inserted_records.extend(replies_response.data)

        except Exception as e:
            print(f"Error inserting comment thread: {e}")

        return inserted_records

    return await asyncio.to_thread(_insert_thread)


async def verify_reel_exists(shortcode: str) -> bool:
    """
    Check if a reel exists before inserting comments.
    
    Args:
        shortcode: Instagram shortcode
        
    Returns:
        bool: True if reel exists, False otherwise
    """
    reel = await get_reel_by_shortcode(shortcode)
    return reel is not None


async def bulk_save_comments(
    comments_list: List[Dict[str, Any]],
    reel_shortcode: str,
    source_shortcode: Optional[str] = None,
) -> int:
    """
    Save multiple comment threads in parallel.

    Args:
        comments_list: List of comment JSON objects
        reel_shortcode: Shortcode of the incident reel (FK, used for grouping all
                        comments about this incident regardless of where they appeared)
        source_shortcode: Shortcode where these comments physically appeared.
                          Defaults to reel_shortcode (non-repost case).

    Returns:
        int: Total number of comments inserted (including replies)
    """
    if not await verify_reel_exists(reel_shortcode):
        raise ValueError(f"Reel with shortcode '{reel_shortcode}' does not exist")

    tasks = [
        save_comment_thread(comment, reel_shortcode, source_shortcode)
        for comment in comments_list
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_inserted = 0
    for result in results:
        if isinstance(result, list):
            total_inserted += len(result)
        elif isinstance(result, Exception):
            print(f"Error in bulk save: {result}")

    return total_inserted


# ── Pipeline run logging (thin CRUD — no domain logic) ────────────────────────

async def insert_pipeline_run(shortcode: str) -> int:
    """
    Insert a new 'running' row into pipeline_runs.

    Returns:
        int: The new row's id — pass this to update_pipeline_run later.
    """
    def _insert():
        supabase = get_supabase_client()
        response = supabase.table("pipeline_runs").insert({
            "shortcode": shortcode,
            "status": "running",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return response.data[0]["id"]

    return await asyncio.to_thread(_insert)


async def update_pipeline_run(run_id: int, data: Dict[str, Any]) -> None:
    """
    Update an existing pipeline_runs row with arbitrary fields.

    Args:
        run_id: Row id returned by insert_pipeline_run
        data:   Dict of columns to update (caller builds this)
    """
    def _update():
        supabase = get_supabase_client()
        supabase.table("pipeline_runs").update(data).eq("id", run_id).execute()

    await asyncio.to_thread(_update)


async def insert_failed_request(
    shortcode: str,
    error: str,
    step: str,
    attempts: int,
) -> None:
    """
    Insert a row into failed_requests for a permanently failed shortcode.

    Args:
        shortcode: Instagram shortcode that exhausted all retry attempts
        error:     Last error message
        step:      Step label where it failed (e.g. "step_5_upload")
        attempts:  Total number of attempts made
    """
    def _insert():
        supabase = get_supabase_client()
        supabase.table("failed_requests").insert({
            "shortcode": shortcode,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "last_error": error,
            "step_failed": step,
            "attempts": attempts,
        }).execute()

    await asyncio.to_thread(_insert)


async def fetch_comments_from_db(shortcode: str) -> List[Dict[str, Any]]:
    """
    Fetch all comments for a given reel from the database.

    Args:
        shortcode: Instagram reel shortcode

    Returns:
        Flat list of comment rows ordered by posted_at descending.
        Call build_comment_tree() in services/comment_parser.py to get nested structure.
    """
    def _fetch():
        supabase = get_supabase_client()
        response = (
            supabase.table("instagram_comments")
            .select("*")
            .eq("reel_shortcode", shortcode)
            .order("posted_at", desc=True)
            .execute()
        )
        return response.data if response.data else []

    return await asyncio.to_thread(_fetch)

