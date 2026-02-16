"""
Supabase Storage Utilities
Async functions for downloading Instagram videos and uploading to Supabase Storage.
"""

import os
import asyncio
from typing import Optional
import aiohttp
import aiofiles
from .supabase_client import get_supabase_client, get_storage_bucket


# Temporary download directory
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_downloads")


async def download_video_stream(url: str, output_path: str) -> str:
    """
    Download a video from URL using streaming to handle large files.
    
    Args:
        url: Video URL (Instagram or other)
        output_path: Local path to save the video
        
    Returns:
        str: Path to downloaded file
        
    Raises:
        Exception: If download fails
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download video: HTTP {response.status}")
            
            async with aiofiles.open(output_path, "wb") as f:
                async for chunk in response.content.iter_chunked(8192):
                    if chunk:
                        await f.write(chunk)
    
    print(f"✓ Downloaded video to {output_path}")
    return output_path


async def upload_to_supabase(local_path: str, bucket_name: str, remote_path: str) -> str:
    """
    Upload a file to Supabase Storage.
    
    Args:
        local_path: Local file path
        bucket_name: Supabase storage bucket name
        remote_path: Remote path within bucket (e.g., "DRLS0KOAdv2.mp4")
        
    Returns:
        str: Storage bucket path
        
    Raises:
        Exception: If upload fails
    """
    def _upload():
        supabase = get_supabase_client()
        
        # Ensure bucket exists (create if needed)
        try:
            supabase.storage.get_bucket(bucket_name)
        except Exception:
            # Bucket doesn't exist, try to create it
            try:
                supabase.storage.create_bucket(bucket_name, options={"public": True})
                print(f"✓ Created storage bucket: {bucket_name}")
            except Exception as e:
                print(f"Note: Could not create bucket (may already exist): {e}")
        
        # Read file and upload
        with open(local_path, "rb") as f:
            file_data = f.read()
            
            response = supabase.storage.from_(bucket_name).upload(
                path=remote_path,
                file=file_data,
                file_options={"content-type": "video/mp4", "upsert": "true"}
            )
        
        return remote_path
    
    result = await asyncio.to_thread(_upload)
    print(f"✓ Uploaded to Supabase Storage: {bucket_name}/{remote_path}")
    return result


async def download_and_upload_reel(video_url: str, shortcode: str, bucket_name: Optional[str] = None) -> str:
    """
    Combined helper: Download Instagram video and upload to Supabase Storage.
    Automatically cleans up temporary files.
    
    Args:
        video_url: Instagram video URL
        shortcode: Instagram shortcode (used for filename)
        bucket_name: Optional bucket name (defaults to env variable or "videos")
        
    Returns:
        str: Storage bucket path (e.g., "DRLS0KOAdv2.mp4")
        
    Example:
        storage_path = await download_and_upload_reel(
            "https://...", 
            "DRLS0KOAdv2"
        )
    """
    if bucket_name is None:
        bucket_name = get_storage_bucket()
    
    # Ensure temp directory exists
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Local temporary path
    temp_path = os.path.join(TEMP_DIR, f"{shortcode}.mp4")
    
    # Remote path in bucket (directly at root, no subdirectory)
    remote_path = f"{shortcode}.mp4"
    
    try:
        # Download video
        await download_video_stream(video_url, temp_path)
        
        # Upload to Supabase
        storage_path = await upload_to_supabase(temp_path, bucket_name, remote_path)
        
        return storage_path
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                print(f"✓ Cleaned up temporary file: {temp_path}")
            except Exception as e:
                print(f"Warning: Could not delete temp file {temp_path}: {e}")


async def get_public_url(bucket_name: str, file_path: str) -> str:
    """
    Get the public URL for a file in Supabase Storage.
    
    Args:
        bucket_name: Storage bucket name
        file_path: Path to file within bucket
        
    Returns:
        str: Public URL
    """
    def _get_url():
        supabase = get_supabase_client()
        response = supabase.storage.from_(bucket_name).get_public_url(file_path)
        return response
    
    return await asyncio.to_thread(_get_url)


async def delete_from_storage(bucket_name: str, file_path: str) -> bool:
    """
    Delete a file from Supabase Storage.
    
    Args:
        bucket_name: Storage bucket name
        file_path: Path to file within bucket
        
    Returns:
        bool: True if successful
    """
    def _delete():
        supabase = get_supabase_client()
        response = supabase.storage.from_(bucket_name).remove([file_path])
        return True
    
    try:
        result = await asyncio.to_thread(_delete)
        print(f"✓ Deleted from storage: {bucket_name}/{file_path}")
        return result
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False

