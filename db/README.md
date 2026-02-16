# Instagram Supabase Integration

This package provides async utilities for storing Instagram reels and comments in Supabase with video storage support.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run SQL Migrations

Execute the SQL files in your Supabase SQL Editor in order:

1. `01_create_reels_table.sql` - Creates the reels table
2. `02_create_comments_table.sql` - Creates the comments table

### 3. Configure Environment Variables

Add to your `.env` file:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_BUCKET=instagram-videos  # Optional, defaults to "instagram-videos"
```

### 4. Create Storage Bucket

In Supabase Dashboard:
- Go to Storage
- Create a new bucket named `instagram-videos` (or your custom name)
- Set privacy settings as needed (public or private)

## Usage

### Quick Start - Process Complete Reel with Comments

```python
import asyncio
from db import save_reel, save_comment_thread, download_and_upload_reel

async def process_instagram_post(reel_json, comments_json):
    """Process a complete Instagram post with video and comments."""
    
    # 1. Download and upload video
    storage_path = await download_and_upload_reel(
        video_url=reel_json['videoUrl'],
        shortcode=reel_json['shortCode']
    )
    print(f"✓ Video stored at: {storage_path}")
    
    # 2. Save reel metadata
    reel_record = await save_reel(reel_json, storage_path)
    print(f"✓ Reel saved: {reel_record['shortcode']}")
    
    # 3. Save all comments with replies
    for comment in comments_json:
        inserted = await save_comment_thread(comment, reel_json['shortCode'])
        print(f"✓ Saved comment thread: {len(inserted)} comments")
    
    return reel_record

# Example data (from your Instagram scraper)
reel_json = {
    "id": "3768188262447963126",
    "shortCode": "DRLS0KOAdv2",
    "caption": "That's one way to get the chores done ✅",
    "ownerId": "71499387366",
    "ownerUsername": "thekeenecrew",
    "timestamp": "2025-11-17T23:46:28.000Z",
    "videoUrl": "https://...",
    "videoViewCount": 4641111,
    "videoPlayCount": 15697353,
    "likesCount": -1,
    "commentsCount": 1250,
    "videoDuration": 36.036
}

comments_json = [
    {
        "id": "17899746144315959",
        "text": "Circle was stressing me out...",
        "ownerUsername": "zariyahjoseph09",
        "timestamp": "2025-11-19T19:33:52.000Z",
        "likesCount": 5935,
        "replies": [
            {
                "id": "17919444018066796",
                "text": "Reply text...",
                "ownerUsername": "cashbarosh",
                "timestamp": "2025-11-25T17:19:23.000Z",
                "likesCount": 16
            }
        ]
    }
]

# Run
asyncio.run(process_instagram_post(reel_json, comments_json))
```

### Individual Functions

#### Save Reel Only (No Video)

```python
from db import save_reel

reel_record = await save_reel(reel_json, storage_path=None)
```

#### Download and Upload Video

```python
from db import download_and_upload_reel

storage_path = await download_and_upload_reel(
    video_url="https://instagram.com/...",
    shortcode="DRLS0KOAdv2"
)
# Returns: "videos/DRLS0KOAdv2.mp4"
```

#### Save Comments Thread

```python
from db import save_comment_thread

# Saves parent comment + all nested replies
inserted_comments = await save_comment_thread(comment_json, "DRLS0KOAdv2")
print(f"Inserted {len(inserted_comments)} comments")
```

#### Bulk Save Multiple Comments

```python
from db import bulk_save_comments

total = await bulk_save_comments(comments_list, "DRLS0KOAdv2")
print(f"Inserted {total} total comments")
```

#### Check if Reel Exists

```python
from db import get_reel_by_shortcode

reel = await get_reel_by_shortcode("DRLS0KOAdv2")
if reel:
    print(f"Reel exists: {reel['caption']}")
```

#### Get Public URL for Video

```python
from db import get_public_url

url = await get_public_url("instagram-videos", "videos/DRLS0KOAdv2.mp4")
print(f"Public URL: {url}")
```

## Database Schema

### raw_instagram_reels

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | Auto-increment primary key |
| instagram_id | TEXT | Instagram post ID (unique) |
| shortcode | TEXT | Instagram shortcode (unique) |
| caption | TEXT | Post caption |
| owner_id | TEXT | Owner's Instagram ID |
| owner_username | TEXT | Owner's username |
| posted_at | TIMESTAMPTZ | When posted on Instagram |
| stats | JSONB | Engagement stats (views, likes, etc.) |
| storage_bucket_path | TEXT | Path in Supabase Storage |
| created_at | TIMESTAMPTZ | When inserted in DB |

### instagram_comments

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | Auto-increment primary key |
| instagram_comment_id | TEXT | Instagram comment ID (unique) |
| reel_shortcode | TEXT | Foreign key to reels |
| parent_comment_id | BIGINT | Self-reference for replies |
| text_content | TEXT | Comment text |
| owner_username | TEXT | Commenter's username |
| like_count | INT | Number of likes |
| posted_at | TIMESTAMPTZ | When posted |
| created_at | TIMESTAMPTZ | When inserted in DB |

## Features

✅ **Async/Await** - Non-blocking I/O for better performance  
✅ **Video Storage** - Automatic download and upload to Supabase Storage  
✅ **Nested Comments** - Supports unlimited reply depth  
✅ **Batch Operations** - Efficient bulk inserts  
✅ **Duplicate Prevention** - Upsert logic prevents duplicates  
✅ **Error Handling** - Graceful failures with logging  
✅ **Temp File Cleanup** - Automatic cleanup after upload  

## Error Handling

All functions include try/except blocks and will print errors to console. For production, integrate with your logging system:

```python
import logging
from db import save_reel

logger = logging.getLogger(__name__)

try:
    reel = await save_reel(reel_json, storage_path)
except Exception as e:
    logger.error(f"Failed to save reel: {e}")
```

## Integration with Existing Code

### With Webhooks

```python
# In routers/webhooks.py
from db import save_reel, bulk_save_comments, download_and_upload_reel

async def handle_instagram_mention(post_data):
    # Download and store video
    storage_path = await download_and_upload_reel(
        post_data['videoUrl'],
        post_data['shortCode']
    )
    
    # Save to database
    reel = await save_reel(post_data, storage_path)
    await bulk_save_comments(post_data['comments'], post_data['shortCode'])
    
    return reel
```

### With Media Processor

```python
# In src/models/media_processor.py
from db import get_reel_by_shortcode, save_reel

async def process_and_analyze(shortcode):
    # Get video from Supabase
    reel = await get_reel_by_shortcode(shortcode)
    
    if reel and reel['storage_bucket_path']:
        # Download from storage and analyze
        video_path = await download_from_storage(reel['storage_bucket_path'])
        analysis = await analyze_video(video_path)
        
        # Update reel with analysis results
        # ... your analysis logic
```

## Performance Notes

- **Parallel Processing**: Use `asyncio.gather()` for multiple operations
- **Batch Inserts**: `bulk_save_comments()` is faster than individual saves
- **Streaming Downloads**: Large videos are streamed in chunks (8KB)
- **Temp Cleanup**: Files are automatically deleted after upload

## Troubleshooting

### "SUPABASE_URL environment variable is required"
- Ensure `.env` file exists with correct variables
- Check that `python-dotenv` is installed

### "Failed to download video: HTTP 403"
- Instagram URL may be expired or require authentication
- Try refreshing the URL from Instagram API

### "Bucket does not exist"
- Create the bucket in Supabase Dashboard → Storage
- Or let the code auto-create it (requires proper permissions)

### Foreign Key Constraint Error
- Ensure reel exists before inserting comments
- Use `verify_reel_exists()` to check first

