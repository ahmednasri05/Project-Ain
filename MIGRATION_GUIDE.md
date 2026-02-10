# Migration Guide: New Modular Analysis System

## Overview of Changes

The crime monitoring system has been completely refactored into a **modular, async architecture** with:

✅ **Parallel processing** - Audio and video analyzed simultaneously  
✅ **Structured outputs** - All results as Pydantic models with JSON schemas  
✅ **Better entity detection** - Weapons, vehicles, license plates, landmarks  
✅ **Detailed crime assessment** - Automated danger scoring and recommendations  
✅ **Modular design** - Use individual analyzers or integrated processor  

## New File Structure

```
src/
├── models/
│   ├── schemas.py              # NEW: Pydantic models for all outputs
│   ├── audio_analyzer.py       # NEW: Audio transcription + analysis
│   ├── video_analyzer.py       # NEW: Video entity detection + crimes
│   ├── media_processor.py      # NEW: Integrated async processor
│   ├── __init__.py             # UPDATED: Exports new modules
│   └── README_NEW.md           # NEW: Detailed documentation
│
├── main_async.py               # NEW: Async main script
├── example_usage.py            # NEW: Usage examples
└── logging_config.py           # UNCHANGED
```

## Quick Start

### 1. Install Dependencies

All required packages are already in `requirements.txt`:
- `openai>=2.3.0` - Audio transcription (Whisper) and analysis
- `google-genai>=1.42.0` - Video analysis (Gemini)
- `pydantic>=2.12.0` - Structured outputs
- `python-dotenv>=1.1.0` - Environment variables

### 2. Set Environment Variables

Ensure your `.env` file has:

```bash
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
```

**IMPORTANT**: Replace the hardcoded Gemini key in notebooks with the env var!

### 3. Run Examples

```bash
cd src

# Full async example with detailed output
python main_async.py

# Or run the examples script
python example_usage.py
```

## API Reference

### Option 1: Integrated Processor (Recommended)

**Best for**: Complete analysis with parallel processing

```python
import asyncio
from models.media_processor import process_media

async def main():
    result = await process_media(
        video_path="path/to/video.mp4",
        audio_path="path/to/audio.mp3",  # Optional
        output_dir="output",
        language="ar"
    )
    
    # Access results
    print(f"Danger: {result.video_analysis.danger_score}/10")
    print(f"Action: {result.recommended_action}")
    
    # Results auto-saved to output/media_analysis_YYYYMMDD_HHMMSS.json

asyncio.run(main())
```

### Option 2: Individual Analyzers

**Best for**: When you only need audio OR video analysis

```python
import asyncio
from models import analyze_audio, analyze_video

async def main():
    # Audio only
    audio_result = await analyze_audio(
        audio_path="audio.mp3",
        language="ar"
    )
    print(f"Transcript: {audio_result.transcript}")
    print(f"Sentiment: {audio_result.sentiment}")
    print(f"Events: {len(audio_result.audio_events)}")
    
    # Video only
    video_result = await analyze_video("video.mp4")
    print(f"Danger: {video_result.danger_score}/10")
    print(f"Crimes: {len(video_result.possible_crimes)}")
    
    # Access detailed entities
    for weapon in video_result.detected_entities.weapons:
        print(f"Weapon: {weapon.type} at {weapon.timestamp}")
    
    for vehicle in video_result.detected_entities.vehicles:
        if vehicle.license_plate:
            print(f"Plate: {vehicle.license_plate.raw_text}")

asyncio.run(main())
```

### Option 3: Class-Based (Advanced)

**Best for**: Custom processing or integration with existing async code

```python
from models import AudioAnalyzer, VideoAnalyzer

async def process_custom(video_path, audio_path):
    # Create analyzers
    audio_analyzer = AudioAnalyzer(api_key="...")  # or reads from env
    video_analyzer = VideoAnalyzer(api_key="...")
    
    # Run in parallel
    audio_result, video_result = await asyncio.gather(
        audio_analyzer.analyze_audio(audio_path),
        video_analyzer.analyze_video(video_path)
    )
    
    # Custom processing here
    return audio_result, video_result
```

## Output Schema

### MediaAnalysisResult

```json
{
  "timestamp": "2025-02-10T12:30:45",
  "video_path": "video.mp4",
  "audio_path": "audio.mp3",
  
  "video_analysis": {
    "description": "Physical altercation between two males near a white sedan.",
    "danger_score": 8,
    "video_duration": "01:23",
    
    "detected_entities": {
      "people_count": 5,
      "weapons": [
        {
          "type": "blunt_object",
          "confidence": 0.94,
          "timestamp": "00:12",
          "description": "Metal rod"
        }
      ],
      "vehicles": [
        {
          "type": "sedan",
          "color": "white",
          "timestamp": "00:00",
          "license_plate": {
            "raw_text": "س ج ط 1234",
            "governorate_guess": "Alexandria",
            "confidence": 0.89
          }
        }
      ],
      "other_objects": ["broken_glass", "mobile_phone"]
    },
    
    "scene_landmarks": {
      "identified_landmark": "Stanley Bridge",
      "architectural_style": "Alexandria Corniche",
      "confidence": 0.98,
      "location_hints": ["coastal_road", "palm_trees"]
    },
    
    "possible_crimes": [
      {
        "content": "Assault with weapon",
        "timestamp": "00:12",
        "rule_violated": "Article 240 - Assault",
        "severity": "severe"
      }
    ],
    
    "quality_notes": "Clear daylight video, good quality"
  },
  
  "audio_analysis": {
    "transcript": "[00:00 - 00:05] يا باشا والله ما عملت حاجة!\n[00:05 - 00:10] ...",
    "sentiment": "Distress/Aggression",
    "language": "ar",
    "confidence": 0.95,
    
    "audio_events": [
      {
        "event": "glass_shattering",
        "timestamp": "00:08",
        "intensity": null
      },
      {
        "event": "aggressive_shouting",
        "timestamp": "00:03",
        "intensity": "high"
      }
    ]
  },
  
  "overall_assessment": "The video depicts a serious physical altercation...",
  "recommended_action": "ALERT: Contact police (122) immediately. Criminal activity detected requiring immediate response."
}
```

## Migration from Old System

### Old Code (aggregator.py)

```python
# OLD - aggregator.py
results = process_video(
    video_path="video.mp4",
    audio_path="audio.mp3",
    output_dir="output"
)

# Access old format
crime_detected = results['crime_classification']['crime_detected']
```

### New Code (Recommended)

```python
# NEW - media_processor.py
import asyncio
from models.media_processor import process_media

async def main():
    result = await process_media(
        video_path="video.mp4",
        audio_path="audio.mp3",
        output_dir="output"
    )
    
    # Access new structured format
    danger_score = result.video_analysis.danger_score
    crimes = result.video_analysis.possible_crimes
    
    # Or as dict for backwards compatibility
    result_dict = result.model_dump()

asyncio.run(main())
```

## Key Differences

| Feature | Old System | New System |
|---------|-----------|------------|
| **Processing** | Sequential | Parallel (async) |
| **Audio** | Whisper only | Whisper + GPT event detection |
| **Video** | Simple caption | Entity detection, landmarks, OCR |
| **Output** | Plain dict | Pydantic models with validation |
| **Crime Detection** | Single classifier | Per-incident with timestamps |
| **Danger Score** | None | 0-10 scale with recommendations |
| **License Plates** | Not detected | OCR with governorate guess |
| **Performance** | ~30-45s | ~10-30s (parallel) |

## Webhook Integration

To integrate with existing webhook system (`routers/webhooks.py`):

```python
# In services/mention.py or similar

import asyncio
from src.models.media_processor import process_media

async def process_mention_async(media_id: str):
    """Process mention with new async system."""
    # Download media (existing code)
    video_path, audio_path = await download_media(media_id)
    
    # Analyze with new system
    result = await process_media(
        video_path=video_path,
        audio_path=audio_path,
        output_dir=f"output/{media_id}"
    )
    
    # Store in database
    await store_analysis(media_id, result.model_dump())
    
    # Check if action needed
    if result.video_analysis.danger_score >= 7:
        await notify_authorities(result)
    
    return result

# Sync wrapper for existing code
def process_mention(media_id: str):
    return asyncio.run(process_mention_async(media_id))
```

## Troubleshooting

### Error: "GEMINI_API_KEY not found"

**Solution**: 
1. Create/update `.env` file with valid key
2. Remove hardcoded keys from notebooks
3. Ensure `python-dotenv` is installed

### Error: "403 PERMISSION_DENIED"

**Solution**: API key is suspended or invalid
1. Go to Google Cloud Console
2. Check project billing status
3. Generate new API key
4. Update `.env`

### Audio file not found

**Solution**: System handles gracefully - video analysis continues, audio returns placeholder

### Import errors

**Solution**: Make sure you're in the correct directory
```bash
cd src
python main_async.py
```

Or use absolute imports in production.

## Performance Tips

1. **Use parallel processing**: Always use `MediaProcessor` for full analysis
2. **Video size**: Gemini accepts up to ~20MB inline; compress larger files
3. **Audio format**: MP3 recommended; WAV also supported
4. **Language**: Specify correct language code for better transcription

## Next Steps

1. ✅ Run `example_usage.py` to see all features
2. ✅ Test with your own media files
3. ✅ Integrate with webhook system if needed
4. ✅ Customize danger thresholds in `media_processor.py`
5. ✅ Add custom crime types or entity detection

## Support

- Documentation: `src/models/README_NEW.md`
- Examples: `src/example_usage.py`
- Schemas: `src/models/schemas.py`
- Legacy code: Keep old files for reference during migration

---

**Questions?** Check the detailed README at `src/models/README_NEW.md`

