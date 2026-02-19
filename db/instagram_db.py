"""
Instagram Database Utilities
Async functions for inserting Instagram reels and comments into Supabase.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from .supabase_client import get_supabase_client


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


async def save_comment_thread(comment_json: Dict[str, Any], reel_shortcode: str) -> List[Dict[str, Any]]:
    """
    Insert a comment and all its nested replies.
    Handles the parent-child relationship recursively.
    
    Args:
        comment_json: Comment JSON with potential nested "replies" array
        reel_shortcode: Shortcode of the parent reel
        
    Returns:
        List[Dict]: List of inserted comment records
        
    Example:
        inserted_comments = await save_comment_thread(comment_json, "DRLS0KOAdv2")
    """
    def _insert_thread():
        supabase = get_supabase_client()
        inserted_records = []
        
        # 1. Insert the PARENT (top-level comment)
        parent_data = {
            "instagram_comment_id": comment_json["id"],
            "reel_shortcode": reel_shortcode,
            "text_content": comment_json.get("text", ""),
            "owner_username": comment_json.get("ownerUsername"),
            "like_count": comment_json.get("likesCount", 0),
            "posted_at": comment_json.get("timestamp"),
            "parent_comment_id": None  # Root comment
        }
        
        try:
            # Try insert, ignore if duplicate
            parent_response = supabase.table("instagram_comments").upsert(
                parent_data,
                on_conflict="instagram_comment_id"
            ).execute()
            
            if parent_response.data:
                parent_record = parent_response.data[0]
                inserted_records.append(parent_record)
                db_parent_id = parent_record["id"]
                
                # 2. Insert REPLIES if they exist
                if "replies" in comment_json and comment_json["replies"]:
                    replies_data = []
                    for reply in comment_json["replies"]:
                        replies_data.append({
                            "instagram_comment_id": reply["id"],
                            "reel_shortcode": reel_shortcode,
                            "text_content": reply.get("text", ""),
                            "owner_username": reply.get("ownerUsername"),
                            "like_count": reply.get("likesCount", 0),
                            "posted_at": reply.get("timestamp"),
                            "parent_comment_id": db_parent_id  # Link to parent
                        })
                    
                    # Batch insert replies
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


async def bulk_save_comments(comments_list: List[Dict[str, Any]], reel_shortcode: str) -> int:
    """
    Save multiple comment threads in parallel.
    
    Args:
        comments_list: List of comment JSON objects
        reel_shortcode: Shortcode of the parent reel
        
    Returns:
        int: Total number of comments inserted (including replies)
    """
    # Verify reel exists first
    if not await verify_reel_exists(reel_shortcode):
        raise ValueError(f"Reel with shortcode '{reel_shortcode}' does not exist")
    
    # Process all comments in parallel
    tasks = [save_comment_thread(comment, reel_shortcode) for comment in comments_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count total inserted
    total_inserted = 0
    for result in results:
        if isinstance(result, list):
            total_inserted += len(result)
        elif isinstance(result, Exception):
            print(f"Error in bulk save: {result}")
    
    return total_inserted

