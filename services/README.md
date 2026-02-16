# Services - Comment Parser & Sentiment Analysis

This directory contains business logic services for processing Instagram comments and sentiment analysis.

## Comment Parser Service

The comment parser fetches comments from the database and formats them for LLM sentiment analysis.

### Features

✅ **Database Integration** - Fetches comments directly from Supabase  
✅ **Tree Structure** - Builds nested comment/reply hierarchies  
✅ **Multiple Formats** - Outputs as text or JSON  
✅ **Flexible Depth** - Control reply nesting depth  
✅ **Metadata Options** - Include/exclude usernames, likes, timestamps  
✅ **Token Optimization** - Extract text-only for minimal LLM tokens  

---

## Quick Start

### 1. Fetch and Format Comments (Text)

```python
from services import get_comments_for_sentiment_analysis

# Get comments as formatted text for LLM
comments_text = await get_comments_for_sentiment_analysis(
    shortcode="DRLS0KOAdv2",
    format_type="text",
    include_metadata=True,
    include_replies=True,
    max_depth=2
)

print(comments_text)
```

**Output:**
```
• Circle was stressing me out. They could've won and he fumbled
  [@zariyahjoseph09, 5935 likes, 2025-11-19 19:33]
  └─ 😂
    [@cashbarosh, 16 likes, 2025-11-25 17:19]
  └─ I came to the comments for this ahaha
    [@paulafadario92, 14 likes, 2025-12-05 22:20]

• والله انت بوت
  [@duarkl_mehuk, 0 likes, 2026-02-15 07:02]
```

### 2. Fetch and Format Comments (JSON)

```python
comments_json = await get_comments_for_sentiment_analysis(
    shortcode="DRLS0KOAdv2",
    format_type="json"
)
```

**Output:**
```json
{
  "total_comments": 2,
  "comments": [
    {
      "text": "Circle was stressing me out...",
      "username": "zariyahjoseph09",
      "likes": 5935,
      "posted_at": "2025-11-19T19:33:52.000Z",
      "replies": [
        {
          "text": "😂",
          "username": "cashbarosh",
          "likes": 16,
          "posted_at": "2025-11-25T17:19:23.000Z"
        }
      ]
    }
  ]
}
```

### 3. Complete Sentiment Analysis Workflow

```python
from services import get_comments_for_sentiment_analysis
from src.models.sentiment_analyzer import SentimentAnalyzer

# Fetch and format comments
comments_text = await get_comments_for_sentiment_analysis("DRLS0KOAdv2")

# Analyze sentiment
analyzer = SentimentAnalyzer()
result = await analyzer.analyze_sentiment(comments_text)

print(f"Label: {result.label}")
print(f"Explanation: {result.explanation}")
```

### 4. Create Complete Prompt with Reel Context

```python
from services import create_sentiment_analysis_prompt, get_comments_for_sentiment_analysis
from db import get_reel_by_shortcode

# Fetch reel and comments
reel = await get_reel_by_shortcode("DRLS0KOAdv2")
comments_text = await get_comments_for_sentiment_analysis("DRLS0KOAdv2")

# Create complete prompt
prompt = create_sentiment_analysis_prompt(
    shortcode="DRLS0KOAdv2",
    reel_caption=reel['caption'],
    comments_text=comments_text
)
```

---

## API Reference

### `get_comments_for_sentiment_analysis()`

Main function to fetch and format comments.

**Parameters:**
- `shortcode` (str): Instagram reel shortcode
- `format_type` (str): `"text"` or `"json"` (default: `"text"`)
- `include_metadata` (bool): Include username, likes, timestamp (default: `True`)
- `include_replies` (bool): Include nested replies (default: `True`)
- `max_depth` (int): Maximum reply nesting depth (default: `2`)

**Returns:** `str` or `Dict[str, Any]` depending on format_type

---

### `fetch_comments_from_db()`

Fetch raw comments from database.

**Parameters:**
- `shortcode` (str): Instagram reel shortcode

**Returns:** `List[Dict[str, Any]]` - Flat list of comments

---

### `build_comment_tree()`

Build nested tree structure from flat comment list.

**Parameters:**
- `comments` (List[Dict]): Flat list of comments

**Returns:** `List[Dict[str, Any]]` - Nested tree with replies

---

### `format_comment_for_llm_text()`

Format comments as human-readable text.

**Parameters:**
- `comments` (List[Dict]): Comment tree
- `include_metadata` (bool): Include user/like info
- `include_replies` (bool): Include nested replies
- `max_depth` (int): Maximum depth

**Returns:** `str` - Formatted text

---

### `format_comment_for_llm_json()`

Format comments as JSON structure.

**Parameters:**
- `comments` (List[Dict]): Comment tree
- `include_replies` (bool): Include nested replies
- `max_depth` (int): Maximum depth

**Returns:** `Dict[str, Any]` - JSON-serializable dict

---

### `create_sentiment_analysis_prompt()`

Create complete prompt with reel context.

**Parameters:**
- `shortcode` (str): Reel shortcode
- `reel_caption` (Optional[str]): Reel caption for context
- `comments_text` (Optional[str]): Pre-formatted comments

**Returns:** `str` - Complete prompt

---

### `extract_comment_texts_only()`

Extract only text content (no metadata) for minimal tokens.

**Parameters:**
- `comments` (List[Dict]): Comment tree

**Returns:** `List[str]` - Flattened list of text strings

---

## Text Format Options

### With Metadata (Default)

```
• Circle was stressing me out. They could've won and he fumbled
  [@zariyahjoseph09, 5935 likes, 2025-11-19 19:33]
  └─ 😂
    [@cashbarosh, 16 likes, 2025-11-25 17:19]
```

### Without Metadata

```
• Circle was stressing me out. They could've won and he fumbled
  └─ 😂
```

### Text Only (No Structure)

```python
texts = extract_comment_texts_only(comment_tree)
# ["Circle was stressing me out...", "😂", "I came to the comments..."]
```

---

## Examples

Run the example workflow:

```bash
cd Project-Ain
python services/example_sentiment_workflow.py
```

This demonstrates:
1. ✅ Fetching reel metadata
2. ✅ Fetching and formatting comments
3. ✅ Creating complete prompt
4. ✅ Analyzing sentiment with LLM
5. ✅ Batch processing comments

---

## Integration with Sentiment Analyzer

The comment parser is designed to work seamlessly with the sentiment analyzer:

```python
# services/comment_parser.py → src/models/sentiment_analyzer.py

# 1. Fetch comments
comments = await get_comments_for_sentiment_analysis("DRLS0KOAdv2")

# 2. Analyze
analyzer = SentimentAnalyzer()
result = await analyzer.analyze_sentiment(comments)

# 3. Handle result
if result.label == "CRIME_REPORT":
    # Alert authorities
    await notify_authorities(shortcode, comments, result)
elif result.label == "SPAM_SARCASM":
    # Mark as non-critical
    await mark_as_spam(shortcode)
```

---

## Token Optimization Tips

### 1. Limit Reply Depth

```python
# Only top-level comments (no replies)
comments = await get_comments_for_sentiment_analysis(
    shortcode="...",
    include_replies=False
)
```

### 2. Remove Metadata

```python
# No usernames/likes/timestamps
comments = await get_comments_for_sentiment_analysis(
    shortcode="...",
    include_metadata=False
)
```

### 3. Text-Only Extraction

```python
# Minimal tokens - just text
from services import fetch_comments_from_db, build_comment_tree, extract_comment_texts_only

flat = await fetch_comments_from_db("...")
tree = build_comment_tree(flat)
texts = extract_comment_texts_only(tree)
batch_text = "\n".join(texts[:10])  # First 10 only
```

### 4. Batch Processing

```python
# Process comments in smaller batches
await analyze_comments_batch("DRLS0KOAdv2", batch_size=5)
```

---

## Use Cases

### Crime Detection Pipeline

```python
async def detect_crime_from_reel(shortcode: str):
    # 1. Get comments
    comments = await get_comments_for_sentiment_analysis(shortcode)
    
    # 2. Analyze
    analyzer = SentimentAnalyzer()
    result = await analyzer.analyze_sentiment(comments)
    
    # 3. Action based on result
    if result.label == "CRIME_REPORT":
        reel = await get_reel_by_shortcode(shortcode)
        await send_alert({
            "reel": reel,
            "comments": comments,
            "analysis": result
        })
```

### Dashboard Statistics

```python
async def get_reel_engagement_summary(shortcode: str):
    # Fetch structured comments
    comments_json = await get_comments_for_sentiment_analysis(
        shortcode,
        format_type="json"
    )
    
    return {
        "total_comments": comments_json["total_comments"],
        "top_comments": comments_json["comments"][:5],
        "engagement_rate": calculate_engagement(comments_json)
    }
```

---

## Error Handling

```python
try:
    comments = await get_comments_for_sentiment_analysis(shortcode)
    if comments == "[No comments found]":
        print("No comments available")
    else:
        result = await analyzer.analyze_sentiment(comments)
except Exception as e:
    logger.error(f"Error processing comments: {e}")
```

---

## Performance Notes

- **Database Queries**: Single query fetches all comments for a reel
- **Tree Building**: O(n) complexity where n = number of comments
- **Formatting**: Fast string operations
- **Async**: All I/O operations are non-blocking

---

## Next Steps

1. ✅ Comment parser is ready to use
2. Integrate with your Instagram scraping pipeline
3. Set up automated sentiment analysis for new reels
4. Create dashboard to visualize sentiment trends
5. Add webhooks for real-time crime alerts

