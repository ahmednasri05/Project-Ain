# Quick Start Guide - New Modular Analysis System

## 🚀 Get Started in 3 Steps

### Step 1: Set Up Environment

```bash
# Ensure you have the API keys in .env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
```

### Step 2: Run Your First Analysis

```bash
cd src
python main_async.py
```

### Step 3: Check Results

Results saved to: `output/media_analysis_YYYYMMDD_HHMMSS.json`

---

## 📝 Basic Usage

### Option 1: Complete Analysis (Recommended)

```python
import asyncio
from models import process_media

async def main():
    result = await process_media(
        video_path="video.mp4",
        audio_path="audio.mp3",  # Optional
        output_dir="output",
        language="ar"
    )
    
    # Quick access to key info
    print(f"Danger: {result.video_analysis.danger_score}/10")
    print(f"Crimes: {len(result.video_analysis.possible_crimes)}")
    print(f"Action: {result.recommended_action}")

asyncio.run(main())
```

### Option 2: Audio or Video Only

```python
from models import analyze_audio, analyze_video

# Audio only
audio = await analyze_audio("audio.mp3", language="ar")
print(f"Sentiment: {audio.sentiment}")

# Video only
video = await analyze_video("video.mp4")
print(f"Danger: {video.danger_score}/10")
```

---

## 📊 What You Get

### Video Analysis
- ✅ Danger score (0-10)
- ✅ Detected weapons with timestamps
- ✅ Vehicles with license plates (OCR)
- ✅ Landmark identification
- ✅ Crime detection with severity
- ✅ People count

### Audio Analysis
- ✅ Timestamped transcription
- ✅ Event detection (shouting, breaking glass, etc.)
- ✅ Sentiment analysis
- ✅ Language detection

### Combined
- ✅ Overall assessment
- ✅ Recommended action
- ✅ JSON output file

---

## 🔍 Example Output

```json
{
  "video_analysis": {
    "danger_score": 8,
    "possible_crimes": [
      {
        "content": "Physical assault with weapon",
        "timestamp": "00:15",
        "rule_violated": "Assault",
        "severity": "severe"
      }
    ],
    "detected_entities": {
      "weapons": [{"type": "knife", "timestamp": "00:15"}],
      "vehicles": [{"type": "sedan", "color": "white"}],
      "people_count": 3
    }
  },
  "audio_analysis": {
    "transcript": "[00:00 - 00:05] يا باشا...",
    "sentiment": "Distress/Aggression",
    "audio_events": [
      {"event": "aggressive_shouting", "timestamp": "00:08"}
    ]
  },
  "recommended_action": "ALERT: Contact police immediately"
}
```

---

## 📁 New Files

| File | Purpose |
|------|---------|
| `src/models/schemas.py` | Data models (Pydantic) |
| `src/models/audio_analyzer.py` | Audio transcription + analysis |
| `src/models/video_analyzer.py` | Video entity detection |
| `src/models/media_processor.py` | Integrated orchestrator |
| `src/main_async.py` | Main entry point |
| `src/example_usage.py` | Usage examples |

---

## ⚡ Performance

- **Old System**: 30-45 seconds (sequential)
- **New System**: 10-30 seconds (parallel)
- **Speedup**: ~50% faster

---

## 🔧 Troubleshooting

### "OPENAI_API_KEY not found"
→ Add to `.env` file in project root

### "403 PERMISSION_DENIED" (Gemini)
→ Check API key is valid and billing enabled

### "Audio file not found"
→ System continues with video-only analysis

### Import errors
→ Run from `src/` directory: `cd src && python main_async.py`

---

## 📚 Full Documentation

- **Complete API**: `src/models/README_NEW.md`
- **Migration**: `MIGRATION_GUIDE.md`
- **Implementation**: `src/IMPLEMENTATION_SUMMARY.md`
- **Examples**: `src/example_usage.py`

---

## 🎯 Next Steps

1. ✅ Run `python main_async.py` to test
2. ✅ Check output in `output/` directory
3. ✅ Read full docs in `src/models/README_NEW.md`
4. ✅ Integrate with your webhook system
5. ✅ Customize danger thresholds if needed

---

**Questions?** Check `src/models/README_NEW.md` for detailed documentation.

