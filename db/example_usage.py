"""
Example Usage: Instagram to Supabase Integration
Demonstrates how to process Instagram reels and comments.
"""

import asyncio
import os
import json
from db import (
    save_reel,
    save_comment_thread,
    bulk_save_comments,
    download_and_upload_reel,
    get_reel_by_shortcode
)


# Sample Instagram reel data (from your scraper)
# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REELS_PATH = os.path.join(SCRIPT_DIR, 'example_reels_payload.json')
COMMENTS_PATH = os.path.join(SCRIPT_DIR, 'example_comments_payload.json')

# Load JSON files (they contain arrays, so we take the first element)
with open(REELS_PATH, 'r', encoding='utf-8') as f:
    reels_data = json.load(f)
    SAMPLE_REEL = reels_data[0] if isinstance(reels_data, list) else reels_data

with open(COMMENTS_PATH, 'r', encoding='utf-8') as f:
    comments_data = json.load(f)
    SAMPLE_COMMENTS = comments_data if isinstance(comments_data, list) else [comments_data]


async def example_1_save_reel_with_video():
    """Example 1: Download video and save reel to database."""
    print("\n=== Example 1: Save Reel with Video ===\n")
    
    # Download and upload video to Supabase Storage
    print("Downloading and uploading video...")
    storage_path = await download_and_upload_reel(
        video_url=SAMPLE_REEL['videoUrl'],
        shortcode=SAMPLE_REEL['shortCode']
    )
    print(f"✓ Video stored at: {storage_path}\n")
    
    # Save reel metadata to database
    print("Saving reel metadata...")
    reel_record = await save_reel(SAMPLE_REEL, storage_path)
    print(f"✓ Reel saved:")
    print(f"  - ID: {reel_record['id']}")
    print(f"  - Shortcode: {reel_record['shortcode']}")
    print(f"  - Owner: {reel_record['owner_username']}")
    print(f"  - Views: {reel_record['stats']['video_view_count']:,}")
    
    return reel_record


async def example_2_save_comments():
    """Example 2: Save comments with nested replies."""
    print("\n=== Example 2: Save Comments ===\n")
    
    shortcode = SAMPLE_REEL['shortCode']
    
    # Save each comment thread
    for i, comment in enumerate(SAMPLE_COMMENTS, 1):
        print(f"Saving comment thread {i}...")
        inserted = await save_comment_thread(comment, shortcode)
        print(f"✓ Inserted {len(inserted)} comments (parent + replies)")
        print(f"  - Parent: {comment['text'][:50]}...")
        print(f"  - Replies: {len(comment.get('replies', []))}")
    
    print(f"\n✓ Total comment threads saved: {len(SAMPLE_COMMENTS)}")


async def example_3_bulk_save_comments():
    """Example 3: Bulk save all comments at once (faster)."""
    print("\n=== Example 3: Bulk Save Comments ===\n")
    
    shortcode = SAMPLE_REEL['shortCode']
    
    print(f"Bulk saving {len(SAMPLE_COMMENTS)} comment threads...")
    total_inserted = await bulk_save_comments(SAMPLE_COMMENTS, shortcode)
    print(f"✓ Total comments inserted: {total_inserted}")


async def example_4_check_existing_reel():
    """Example 4: Check if reel already exists."""
    print("\n=== Example 4: Check Existing Reel ===\n")
    
    shortcode = SAMPLE_REEL['shortCode']
    
    print(f"Looking up reel: {shortcode}")
    reel = await get_reel_by_shortcode(shortcode)
    
    if reel:
        print(f"✓ Reel found:")
        print(f"  - Caption: {reel['caption'][:50]}...")
        print(f"  - Posted: {reel['posted_at']}")
        print(f"  - Storage: {reel['storage_bucket_path']}")
    else:
        print("✗ Reel not found")
    
    return reel


async def example_5_complete_workflow():
    """Example 5: Complete workflow - reel + video + comments."""
    print("\n=== Example 5: Complete Workflow ===\n")
    
    shortcode = SAMPLE_REEL['shortCode']
    
    # Check if already exists
    existing = await get_reel_by_shortcode(shortcode)
    if existing:
        print(f"⚠ Reel already exists (ID: {existing['id']})")
        print("Skipping video download, will update metadata...\n")
        storage_path = existing['storage_bucket_path']
    else:
        # Download and upload video
        print("1. Downloading and uploading video...")
        storage_path = await download_and_upload_reel(
            video_url=SAMPLE_REEL['videoUrl'],
            shortcode=shortcode
        )
        print(f"✓ Video stored\n")
    
    # Save/update reel
    print("2. Saving reel metadata...")
    reel_record = await save_reel(SAMPLE_REEL, storage_path)
    print(f"✓ Reel saved (ID: {reel_record['id']})\n")
    
    # Save comments
    print("3. Saving comments...")
    total_comments = await bulk_save_comments(SAMPLE_COMMENTS, shortcode)
    print(f"✓ {total_comments} comments saved\n")
    
    print("=" * 50)
    print("✓ Complete workflow finished successfully!")
    print("=" * 50)


async def main():
    """Run all examples."""
    print("\n" + "=" * 50)
    print("Instagram to Supabase Integration Examples")
    print("=" * 50)
    
    try:
        # Run complete workflow
        await example_5_complete_workflow()
        
        # Verify it was saved
        await example_4_check_existing_reel()
        
        print("\n✓ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())

