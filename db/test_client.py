from supabase_client import get_supabase_client, get_storage_bucket

async def test_supabase_connection():
    """Test connection to Supabase and basic operations."""
    print("\n=== Testing Supabase Connection ===\n")
    
    try:
        # Get client
        supabase = get_supabase_client()
        print("✓ Supabase client initialized successfully")
        
        # Test fetching from a table (e.g., 'raw_instagram_reels')
        response = await supabase.from_('raw_instagram_reels').select('*').limit(1).execute()
        if response.error:
            print(f"✗ Error fetching from 'raw_instagram_reels' table: {response.error.message}")
        else:
            print(f"✓ Successfully fetched from 'raw_instagram_reels' table: {response.data}")
        
        # Test storage bucket access
        bucket_name = get_storage_bucket()
        print(f"✓ Storage bucket name: {bucket_name}")
        
    except Exception as e:
        print(f"✗ Supabase connection test failed: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_supabase_connection())