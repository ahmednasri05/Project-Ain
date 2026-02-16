# Supabase Setup Guide

Quick setup instructions for the Instagram Supabase integration.

## Step 1: Install Dependencies

```bash
cd "C:\Users\shels\Documents\wezareit el dakhleya\Project-Ain"
pip install -r requirements.txt
```

This will install:
- `supabase>=2.0.0` - Supabase Python client
- `postgrest-py>=0.13.0` - PostgreSQL REST API client

## Step 2: Configure Environment Variables

Your `.env` file should already have these (verify):

```env
SUPABASE_URL=https://lbhhhypaetweknyoeonq.supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_BUCKET=instagram-videos
```

**Note**: Replace `your-anon-key-here` with your actual Supabase anon/public key.

### Where to Find Your Keys:

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Go to **Settings** → **API**
4. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon/public key** → `SUPABASE_KEY`

## Step 3: Run SQL Migrations

In Supabase Dashboard:

1. Go to **SQL Editor**
2. Click **New Query**
3. Copy and paste the contents of `01_create_reels_table.sql`
4. Click **Run**
5. Repeat for `02_create_comments_table.sql`

### Quick Copy-Paste:

**File 1: Create Reels Table**
```sql
-- Copy from: db/01_create_reels_table.sql
```

**File 2: Create Comments Table**
```sql
-- Copy from: db/02_create_comments_table.sql
```

## Step 4: Create Storage Bucket

In Supabase Dashboard:

1. Go to **Storage**
2. Click **New bucket**
3. Name: `instagram-videos`
4. Set **Public bucket**: OFF (keep private)
5. Click **Create bucket**

### Bucket Policies (Optional)

If you want to make videos publicly accessible:

1. Click on the bucket
2. Go to **Policies**
3. Add a policy for public read access

## Step 5: Test the Integration

Run the example script:

```bash
cd "C:\Users\shels\Documents\wezareit el dakhleya\Project-Ain"
python -m db.example_usage
```

This will:
- ✓ Download a sample Instagram video
- ✓ Upload it to Supabase Storage
- ✓ Save reel metadata to database
- ✓ Save comments with nested replies

## Step 6: Verify in Supabase

### Check Database Tables:

1. Go to **Table Editor**
2. You should see:
   - `raw_instagram_reels` - with 1 row
   - `instagram_comments` - with multiple rows

### Check Storage:

1. Go to **Storage** → `instagram-videos`
2. You should see: `videos/DRLS0KOAdv2.mp4`

## Troubleshooting

### "Module not found: supabase"

```bash
pip install supabase
```

### "SUPABASE_KEY environment variable is required"

- Check that `.env` file exists in `Project-Ain/` directory
- Verify the key is correctly set (no quotes needed)
- Restart your terminal/IDE after editing `.env`

### "relation 'raw_instagram_reels' does not exist"

- Run the SQL migrations (Step 3)
- Ensure you're connected to the correct Supabase project

### "Storage bucket not found"

- Create the bucket in Supabase Dashboard (Step 4)
- Or let the code auto-create it (requires admin permissions)

### "Failed to download video: HTTP 403"

- Instagram URLs expire after some time
- Use a fresh URL from your Instagram scraper
- The example uses a placeholder URL - replace with real one

## Usage in Your Code

### Basic Example:

```python
import asyncio
from db import save_reel, bulk_save_comments, download_and_upload_reel

async def process_post(reel_json, comments_json):
    # Download and store video
    storage_path = await download_and_upload_reel(
        reel_json['videoUrl'],
        reel_json['shortCode']
    )
    
    # Save to database
    reel = await save_reel(reel_json, storage_path)
    total = await bulk_save_comments(comments_json, reel_json['shortCode'])
    
    print(f"✓ Saved reel and {total} comments")
    return reel

# Run it
asyncio.run(process_post(reel_json, comments_json))
```

## Next Steps

1. ✅ Integration is ready to use
2. Integrate with your Instagram scraper
3. Add to your webhook handlers (if applicable)
4. Set up automated backups in Supabase
5. Configure Row Level Security policies (optional)

## File Structure

```
Project-Ain/
├── db/
│   ├── __init__.py              # Package exports
│   ├── supabase_client.py       # Client singleton
│   ├── instagram_db.py          # Database operations
│   ├── storage_utils.py         # Video download/upload
│   ├── example_usage.py         # Usage examples
│   ├── README.md                # Full documentation
│   ├── SETUP_GUIDE.md           # This file
│   ├── 01_create_reels_table.sql
│   └── 02_create_comments_table.sql
└── .env                         # Your credentials
```

## Support

For more detailed documentation, see [`db/README.md`](README.md)

For Supabase help, visit [Supabase Docs](https://supabase.com/docs)

