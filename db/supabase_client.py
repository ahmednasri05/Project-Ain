"""
Supabase Client Singleton
Manages the connection to Supabase using credentials from environment variables.
"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Singleton instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create the Supabase client singleton.
    
    Returns:
        Client: Configured Supabase client instance
        
    Raises:
        ValueError: If required environment variables are missing
    """
    global _supabase_client
    
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not key:
            raise ValueError("SUPABASE_KEY or SUPABASE_ANON_KEY environment variable is required")
        
        _supabase_client = create_client(url, key)
    
    return _supabase_client


def get_storage_bucket() -> str:
    """
    Get the storage bucket name from environment or use default.
    
    Returns:
        str: Storage bucket name
    """
    return os.getenv("BUCKET_NAME", "videos")

