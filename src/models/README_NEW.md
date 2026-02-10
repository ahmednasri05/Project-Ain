# Crime Monitoring AI - Modular Analysis System

## Overview

This modular system provides comprehensive video and audio analysis for crime detection with:
- **Parallel Processing**: Audio and video analyzed simultaneously using async/await
- **Structured Outputs**: All results returned as Pydantic models with detailed JSON schemas
- **Entity Detection**: Weapons, vehicles, license plates, landmarks
- **Crime Assessment**: Automated danger scoring and recommended actions
- **Audio Analysis**: Transcription, event detection, sentiment analysis

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MediaProcessor                            │
│                  (Orchestrates Everything)                   │
└────────────────┬─────────────────────────┬──────────────────┘
                 │                         │
        ┌────────▼────────┐       ┌────────▼────────┐
        │ AudioAnalyzer   │       │ VideoAnalyzer   │
        │  (OpenAI)       │       │   (Gemini)      │
        └────────┬────────┘       └────────┬────────┘
                 │                         │
        ┌────────▼────────┐       ┌────────▼────────┐
        │ AudioAnalysis   │       │ VideoAnalysis   │
        │   (Pydantic)    │       │   (Pydantic)    │
        └─────────────────┘       └─────────────────┘
                     │                     │
                     └──────────┬──────────┘
                                │
                     ┌──────────▼─────────────┐
                     │ MediaAnalysisResult    │
                     │   (Combined Result)    │
                     └────────────────────────┘
```

## Modules

### 1. `schemas.py` - Data Models

Pydantic models for all outputs:
- `AudioAnalysis`: Transcript, events, sentiment
- `VideoAnalysis`: Description, entities, crimes, danger score
- `MediaAnalysisResult`: Combined analysis result
- Supporting models: `Weapon`, `Vehicle`, `LicensePlate`, `PossibleCrime`, etc.

### 2. `audio_analyzer.py` - Audio Processing

**Class**: `AudioAnalyzer`
- Uses OpenAI Whisper for transcription
- Uses GPT-4 for event detection and sentiment analysis
- Detects: shouting, glass breaking, gunshots, physical altercations, etc.

**Methods**:
```python
async def transcribe_audio(audio_path: str, language: str = "ar") -> str
async def analyze_audio(audio_path: str, language: str = "ar") -> AudioAnalysis
```

**Output Schema**:
```json
{
  "transcript": "[00:00 - 00:05] Arabic text here...",
  "audio_events": [
    {"event": "aggressive_shouting", "timestamp": "00:12", "intensity": "high"}
  ],
  "sentiment": "Distress/Aggression",
  "language": "ar",
  "confidence": 0.95
}
```

### 3. `video_analyzer.py` - Video Processing

**Class**: `VideoAnalyzer`
- Uses Google Gemini 2.0 Flash for video understanding
- Detects entities, landmarks, license plates
- Assesses danger and identifies crimes

**Methods**:
```python
async def analyze_video(video_path: str) -> VideoAnalysis
```

**Output Schema**:
```json
{
  "description": "Physical altercation between two males...",
  "detected_entities": {
    "weapons": [{"type": "blunt_object", "confidence": 0.94, "timestamp": "00:12"}],
    "vehicles": [
      {
        "type": "sedan",
        "color": "white",
        "license_plate": {
          "raw_text": "س ج ط 1234",
          "governorate_guess": "Alexandria",
          "confidence": 0.89
        }
      }
    ],
    "people_count": 5
  },
  "scene_landmarks": {
    "identified_landmark": "Stanley Bridge",
    "architectural_style": "Alexandria Corniche",
    "confidence": 0.98
  },
  "possible_crimes": [
    {
      "content": "Assault with weapon",
      "timestamp": "00:12",
      "rule_violated": "Article 240 - Assault",
      "severity": "severe"
    }
  ],
  "danger_score": 8
}
```

### 4. `media_processor.py` - Integrated Processing

**Class**: `MediaProcessor`
- Orchestrates parallel audio and video analysis
- Generates overall assessment and recommended actions
- Saves results to JSON

**Methods**:
```python
async def process_media(
    video_path: str,
    audio_path: Optional[str] = None,
    output_dir: str = "output",
    language: str = "ar"
) -> MediaAnalysisResult
```

## Usage Examples

### Example 1: Integrated Processing (Recommended)

```python
import asyncio
from models.media_processor import process_media

async def main():
    result = await process_media(
        video_path="video.mp4",
        audio_path="audio.mp3",  # Optional
        output_dir="output",
        language="ar"
    )
    
    print(f"Danger Score: {result.video_analysis.danger_score}/10")
    print(f"Crimes: {len(result.video_analysis.possible_crimes)}")
    print(f"Action: {result.recommended_action}")

asyncio.run(main())
```

### Example 2: Individual Analyzers

```python
from models.audio_analyzer import analyze_audio
from models.video_analyzer import analyze_video

async def main():
    # Analyze separately
    audio_result = await analyze_audio("audio.mp3")
    video_result = await analyze_video("video.mp4")
    
    # Process results
    print(f"Audio sentiment: {audio_result.sentiment}")
    print(f"Video danger: {video_result.danger_score}")

asyncio.run(main())
```

### Example 3: Using Classes Directly

```python
from models.audio_analyzer import AudioAnalyzer
from models.video_analyzer import VideoAnalyzer

async def main():
    # Create analyzers
    audio_analyzer = AudioAnalyzer()
    video_analyzer = VideoAnalyzer()
    
    # Run in parallel
    audio_task = audio_analyzer.analyze_audio("audio.mp3")
    video_task = video_analyzer.analyze_video("video.mp4")
    
    audio_result, video_result = await asyncio.gather(
        audio_task,
        video_task
    )

asyncio.run(main())
```

## Environment Variables

Required environment variables in `.env`:

```bash
# OpenAI (for audio transcription and analysis)
OPENAI_API_KEY=sk-...

# Google Gemini (for video analysis)
GEMINI_API_KEY=AIza...
```

## Output Files

Results are automatically saved to the specified output directory:

**Filename**: `media_analysis_YYYYMMDD_HHMMSS.json`

**Contents**:
```json
{
  "timestamp": "2025-02-10T...",
  "video_path": "...",
  "audio_path": "...",
  "video_analysis": { ... },
  "audio_analysis": { ... },
  "overall_assessment": "...",
  "recommended_action": "..."
}
```

## Danger Score Scale

- **0-2**: Safe, no concerns
- **3-4**: Minor concern, monitor
- **5-6**: Moderate danger, assess situation
- **7-8**: Serious danger, contact authorities
- **9-10**: Critical emergency, immediate response

## Recommended Actions

Based on danger score and detected crimes:

- **Critical (9-10)**: "URGENT: Contact emergency services immediately (122)"
- **Serious (7-8)**: "ALERT: Contact police (122) immediately"
- **Moderate (5-6)**: "WARNING: Monitor and consider reporting"
- **Low (3-4)**: "CAUTION: Document and assess"
- **Safe (0-2)**: "INFORMATION: No immediate danger"

## Performance

- **Parallel Processing**: Audio and video analyzed simultaneously
- **Typical Duration**: 10-30 seconds for 30-second video
- **Dependencies**: OpenAI API (Whisper + GPT), Google Gemini API

## Error Handling

- Graceful fallback if audio file missing
- Detailed error logging
- Partial results returned when possible
- API errors caught and logged

## Integration with Existing System

This modular system can be integrated with:
- **Webhooks**: Process media from social media mentions
- **Database**: Store results in MongoDB via `services/database.py`
- **Reporting**: Generate reports via `configs/reporting_config.yaml`

## Testing

Run the example script:

```bash
cd src
python example_usage.py
```

Or the full async main:

```bash
cd src
python main_async.py
```

