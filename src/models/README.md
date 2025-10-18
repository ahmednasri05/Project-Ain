# Crime Monitoring AI - Models

## Quick Start

### 1. Setup Environment Variables
Ensure your `.env` file contains:
```
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
```

### 2. Usage Example

```python
from models.aggregator import process_video

# Process a video with its audio
results = process_video(
    video_path="path/to/video.mp4",
    audio_path="path/to/audio.mp3",
    output_dir="output"
)

# Results are automatically saved to JSON in output directory
print(results['crime_classification']['analysis'])
```

### 3. Run Main Script

```bash
cd src
python main.py
```

## Modules

- **audio_transcriber.py**: Transcribes Arabic audio using OpenAI Whisper with timestamps
- **video_captioner.py**: Generates video descriptions using Google Gemini with timestamps
- **text_classifier.py**: Classifies content for criminal activity using GPT-4 with Pydantic validation
- **aggregator.py**: Orchestrates the entire pipeline and saves results

## Pydantic Validation

The `CrimeClassification` model ensures structured output:

```python
from models import CrimeClassification

class CrimeClassification(BaseModel):
    crime_detected: Literal["YES", "NO"]
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]
    type_of_crime: str  # Auto-corrects to "N/A" if no crime detected
    summary: str
    key_evidence: List[str]
```

Benefits:
- **Type Safety**: Ensures crime_detected is only "YES" or "NO"
- **Validation**: Automatically validates confidence levels
- **Auto-correction**: Sets type_of_crime to "N/A" when no crime detected
- **Structured Output**: Guarantees consistent JSON format

## Logging

Comprehensive logging is implemented throughout the pipeline:

- **INFO Level**: High-level progress and results
  - Pipeline start/completion
  - Each processing step completion
  - Final classification results
  
- **DEBUG Level**: Detailed execution information
  - API request details
  - Data previews (first 200 chars)
  - Raw API responses
  - Video file sizes
  
- **ERROR Level**: Error tracking with full stack traces
  - API failures
  - Validation errors
  - File I/O issues

**Log File**: `crime_monitoring.log` (UTF-8 encoded, supports Arabic)

**Change Log Level**:
```python
from logging_config import setup_logging
setup_logging(log_level="DEBUG")  # Options: DEBUG, INFO, WARNING, ERROR
```

## Output

Results are saved as JSON files with:
- Audio transcript (with timestamps)
- Video caption (with timestamps)
- Crime classification (validated Pydantic model):
  - crime_detected: YES/NO
  - confidence_level: HIGH/MEDIUM/LOW
  - type_of_crime: Crime type or N/A
  - summary: Brief explanation
  - key_evidence: List of supporting evidence with timestamps
- Processing timestamps and file paths

All outputs and logs support Arabic text with UTF-8 encoding.

