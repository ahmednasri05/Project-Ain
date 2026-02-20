"""
Supabase Storage Utilities
Async functions for uploading files to and managing Supabase Storage.
"""

import os
import asyncio
import mimetypes
from typing import Optional
from .client import get_supabase_client, get_storage_bucket


def _content_type_for(file_path: str) -> str:
    """
    Infer MIME content-type from file extension.
    Falls back to 'application/octet-stream' for unknown types.
    """
    mime, _ = mimetypes.guess_type(file_path)
    return mime or "application/octet-stream"


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
        content_type = _content_type_for(local_path)
        with open(local_path, "rb") as f:
            file_data = f.read()

            response = supabase.storage.from_(bucket_name).upload(
                path=remote_path,
                file=file_data,
                file_options={"content-type": content_type, "upsert": "true"}
            )
        
        return remote_path
    
    result = await asyncio.to_thread(_upload)
    print(f"✓ Uploaded to Supabase Storage: {bucket_name}/{remote_path}")
    return result


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
        supabase.storage.from_(bucket_name).remove([file_path])
        return True
    
    try:
        result = await asyncio.to_thread(_delete)
        print(f"✓ Deleted from storage: {bucket_name}/{file_path}")
        return result
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False


def upload_large_file(bucket_name: str, file_path: str, destination_path: str) -> None:
    """
    Upload a large file to Supabase Storage in 5 MB chunks.
    Use this instead of upload_to_supabase when regular uploads fail with
    httpx connection errors on large video files.

    Args:
        bucket_name:      Supabase storage bucket name
        file_path:        Local path to the file to upload
        destination_path: Destination path within the bucket

    Raises:
        Exception: If any chunk upload fails
    """
    client = get_supabase_client()
    file_size = os.path.getsize(file_path)
    chunk_size = 5 * 1024 * 1024  # 5 MB

    with open(file_path, "rb") as f:
        for chunk_start in range(0, file_size, chunk_size):
            chunk = f.read(chunk_size)
            headers = {
                "Content-Range": f"bytes {chunk_start}-{chunk_start + len(chunk) - 1}/{file_size}"
            }
            response = client.storage.from_(bucket_name).upload(
                destination_path, chunk, headers
            )
            if not response:
                raise Exception(f"Failed to upload chunk at byte {chunk_start}")

    print(f"✓ Large file uploaded: {bucket_name}/{destination_path}")

