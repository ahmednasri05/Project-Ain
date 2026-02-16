## Video Duplicate Detection System

Perceptual hashing-based duplicate detection for Instagram reels using frame sampling and Hamming distance comparison.

## Overview

This system generates 64-bit perceptual hashes (pHash) from video frames and uses Hamming distance to detect visually similar videos, even if they've been re-encoded, resized, or slightly edited.

## How It Works

### 1. **Frame Sampling**
- Video is sampled every N seconds (default: 2s)
- Each frame is converted to a perceptual hash
- Hash represents visual content in 64 bits

### 2. **Perceptual Hash (pHash)**
- 64-bit fingerprint of image content
- Resistant to minor changes (compression, scaling, color shifts)
- Similar images → similar hashes

### 3. **Hamming Distance**
- Measures similarity between two hashes
- Counts differing bits using XOR operation
- Distance < 5 bits = ~92% visual similarity

### 4. **Duplicate Detection**
- Compare new video's hashes against database
- Find videos with multiple matching frames
- Require minimum matching frames (default: 3)

## Quick Start

### Install Dependencies

```bash
pip install opencv-python imagehash Pillow
```

### Basic Usage

```python
from services import generate_video_fingerprint, check_and_save_fingerprints

# Generate fingerprints
fingerprints = await generate_video_fingerprint("video.mp4")

# Check for duplicates and save if unique
result = await check_and_save_fingerprints("DRLS0KOAdv2", fingerprints)

if result['is_duplicate']:
    print(f"Duplicate of: {result['duplicates'][0]['shortcode']}")
else:
    print(f"Unique video - saved {result['fingerprints_count']} fingerprints")
```

## API Reference

### `generate_video_fingerprint(video_path, interval_seconds=2)`

Extract frames and compute perceptual hashes.

**Parameters:**
- `video_path` (str): Path to video file
- `interval_seconds` (int): Sampling interval (default: 2)

**Returns:**
```python
[
    {"timestamp_seconds": 0.0, "hash": "1101001..."},
    {"timestamp_seconds": 2.0, "hash": "1100110..."},
    ...
]
```

---

### `check_and_save_fingerprints(shortcode, fingerprints, hamming_threshold=5, min_matching_frames=3)`

**Main API**: Check for duplicates FIRST, only save if no duplicates found.

**Parameters:**
- `shortcode` (str): Instagram reel shortcode
- `fingerprints` (list): Output from `generate_video_fingerprint()`
- `hamming_threshold` (int): Max Hamming distance for match (default: 5)
- `min_matching_frames` (int): Min matching frames to consider duplicate (default: 3)

**Returns (Duplicate):**
```python
{
    "is_duplicate": True,
    "duplicates": [
        {
            "shortcode": "ABC123XYZ",
            "matching_frames": 15,
            "total_frames_checked": 18,
            "similarity": 0.95,
            "best_hamming_distance": 2,
            "avg_hamming_distance": 3.2
        }
    ]
}
```

**Returns (Unique - Saved):**
```python
{
    "is_duplicate": False,
    "saved": True,
    "fingerprints_count": 18,
    "shortcode": "DRLS0KOAdv2"
}
```

---

### `find_duplicate_videos(fingerprints, hamming_threshold=5, min_matching_frames=3)`

Search database for similar videos (internal use).

**Returns:** List of matching videos with similarity metrics

---

### `save_video_hashes(shortcode, fingerprints)`

Save fingerprints to database (internal use - called by `check_and_save_fingerprints`).

## Complete Workflow

### Process New Instagram Reel

```python
from services import generate_video_fingerprint, check_and_save_fingerprints
from db import download_and_upload_reel, save_reel

async def process_reel(video_url, shortcode, reel_json):
    # 1. Download video
    temp_path = f"temp/{shortcode}.mp4"
    await download_video_stream(video_url, temp_path)
    
    # 2. Generate fingerprints
    fingerprints = await generate_video_fingerprint(temp_path)
    
    # 3. Check for duplicates and save if unique
    result = await check_and_save_fingerprints(shortcode, fingerprints)
    
    if result['is_duplicate']:
        # DUPLICATE DETECTED - Don't upload or process
        print(f"⚠ Duplicate of: {result['duplicates'][0]['shortcode']}")
        os.remove(temp_path)
        return {"status": "duplicate"}
    
    # 4. Upload to storage (only if unique)
    storage_path = await upload_to_supabase(temp_path, "videos", f"{shortcode}.mp4")
    
    # 5. Save reel metadata
    reel = await save_reel(reel_json, storage_path)
    
    # 6. Continue with comments, analysis, etc.
    os.remove(temp_path)
    return {"status": "success", "reel_id": reel['id']}
```

## Database Schema

```sql
CREATE TABLE video_frames (
  id BIGINT PRIMARY KEY,
  reel_shortcode TEXT REFERENCES raw_instagram_reels(shortcode),
  timestamp_seconds REAL,
  phash BIT(64),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- GIST index for fast Hamming distance queries
CREATE INDEX idx_frames_phash ON video_frames USING GIST (phash);
```

## Configuration

### Adjust Sensitivity

```python
# More strict (fewer false positives)
result = await check_and_save_fingerprints(
    shortcode,
    fingerprints,
    hamming_threshold=3,      # Stricter (default: 5)
    min_matching_frames=5     # More frames required (default: 3)
)

# More lenient (catch more duplicates)
result = await check_and_save_fingerprints(
    shortcode,
    fingerprints,
    hamming_threshold=8,      # More lenient
    min_matching_frames=2     # Fewer frames required
)
```

### Adjust Sampling Rate

```python
# Sample every 1 second (more fingerprints, slower)
fingerprints = await generate_video_fingerprint(video_path, interval_seconds=1)

# Sample every 5 seconds (fewer fingerprints, faster)
fingerprints = await generate_video_fingerprint(video_path, interval_seconds=5)
```

## Performance

### Typical Video (30 seconds)
- **Sampling (2s intervals)**: ~15 frames
- **Fingerprint generation**: ~2-3 seconds
- **Database query**: <100ms (with GIST index)
- **Total**: ~3 seconds

### Scalability
- **GIST Index**: Enables fast bitwise operations on millions of rows
- **Batch Insert**: All frames inserted in single transaction
- **Async Operations**: Non-blocking I/O

## Use Cases

### 1. Prevent Duplicate Processing
```python
result = await check_and_save_fingerprints(shortcode, fingerprints)
if result['is_duplicate']:
    # Skip expensive video analysis
    return
```

### 2. Content Moderation
```python
# Find all duplicates of a specific video
duplicates = await find_duplicate_videos(original_fingerprints)
for dup in duplicates:
    await flag_as_duplicate(dup['shortcode'])
```

### 3. Analytics
```python
# Track viral content spread
if result['is_duplicate']:
    await track_repost({
        "original": result['duplicates'][0]['shortcode'],
        "repost": shortcode,
        "similarity": result['duplicates'][0]['similarity']
    })
```

## Limitations

### What It Detects
✅ Re-uploads of same video  
✅ Videos with different compression  
✅ Videos with different resolution  
✅ Videos with slight color/brightness changes  
✅ Videos with minor cropping  

### What It Doesn't Detect
❌ Completely different videos  
❌ Videos with heavy editing/filters  
❌ Videos with added overlays/text  
❌ Flipped/mirrored videos (can be added)  

## Troubleshooting

### "Could not open video"
- Check video file path
- Ensure video format is supported (MP4, AVI, MOV)
- Verify file is not corrupted

### "No duplicates found" (but should be)
- Decrease `hamming_threshold` (e.g., 8)
- Decrease `min_matching_frames` (e.g., 2)
- Increase sampling rate (e.g., 1 second)

### "Too many false positives"
- Increase `hamming_threshold` (e.g., 3)
- Increase `min_matching_frames` (e.g., 5)
- Decrease sampling rate (e.g., 3 seconds)

## Examples

Run the example script:

```bash
cd Project-Ain
python services/example_duplicate_detection.py
```

See [`example_duplicate_detection.py`](example_duplicate_detection.py) for complete working examples.

