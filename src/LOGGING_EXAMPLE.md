# Logging Output Examples

## Sample Log Output (INFO Level)

```
2025-10-10 14:30:15,123 - __main__ - INFO - Crime Monitoring AI - Starting application
2025-10-10 14:30:15,125 - models.aggregator - INFO - ============================================================
2025-10-10 14:30:15,125 - models.aggregator - INFO - Starting video processing pipeline
2025-10-10 14:30:15,125 - models.aggregator - INFO - ============================================================
2025-10-10 14:30:15,126 - models.aggregator - INFO - Video path: C:\Users\shels\Downloads\dakhleya videos\women brutality stairs\women brutality stairs.mp4
2025-10-10 14:30:15,126 - models.aggregator - INFO - Audio path: C:\Users\shels\Documents\wezareit el dakhleya\Gold thiefs.mp3
2025-10-10 14:30:15,126 - models.aggregator - INFO - 
[STEP 1/3] Audio Transcription
2025-10-10 14:30:15,127 - models.audio_transcriber - INFO - Starting audio transcription for: C:\Users\shels\Documents\wezareit el dakhleya\Gold thiefs.mp3
2025-10-10 14:30:18,456 - models.audio_transcriber - INFO - Audio transcription completed. Total length: 1245 characters
2025-10-10 14:30:18,456 - models.aggregator - INFO - ✓ Audio transcription complete
2025-10-10 14:30:18,457 - models.aggregator - INFO - 
[STEP 2/3] Video Captioning
2025-10-10 14:30:18,458 - models.video_captioner - INFO - Starting video captioning for: C:\Users\shels\Downloads\dakhleya videos\women brutality stairs\women brutality stairs.mp4
2025-10-10 14:30:25,789 - models.video_captioner - INFO - Video captioning completed. Caption length: 2156 characters
2025-10-10 14:30:25,790 - models.aggregator - INFO - ✓ Video captioning complete
2025-10-10 14:30:25,790 - models.aggregator - INFO - 
[STEP 3/3] Crime Classification
2025-10-10 14:30:25,791 - models.text_classifier - INFO - Starting crime classification...
2025-10-10 14:30:28,234 - models.text_classifier - INFO - Crime classification completed: YES (Confidence: HIGH, Type: Assault)
2025-10-10 14:30:28,235 - models.aggregator - INFO - ✓ Crime classification complete
2025-10-10 14:30:28,240 - models.aggregator - INFO - 
============================================================
2025-10-10 14:30:28,240 - models.aggregator - INFO - Pipeline completed successfully in 13.12 seconds
2025-10-10 14:30:28,240 - models.aggregator - INFO - Results saved to: output\analysis_20251010_143028.json
2025-10-10 14:30:28,240 - models.aggregator - INFO - 
============================================================
```

## Sample Log Output (DEBUG Level)

```
2025-10-10 14:30:15,127 - models.audio_transcriber - DEBUG - Sending audio to OpenAI Whisper API...
2025-10-10 14:30:18,450 - models.audio_transcriber - DEBUG - Received 15 segments from API
2025-10-10 14:30:18,455 - models.audio_transcriber - DEBUG - Transcription preview: [00:00 - 00:05] الاتنين دول حرامية، الاتنين دول سرقوا مننا خاتم في الفرع وطلعوا وجريوا ملامحهم واضحة جدا هنا...

2025-10-10 14:30:18,458 - models.video_captioner - DEBUG - Video size: 18.45 MB
2025-10-10 14:30:18,459 - models.video_captioner - DEBUG - Sending video to Gemini API...
2025-10-10 14:30:25,788 - models.video_captioner - DEBUG - Caption preview: The video, likely captured by a security camera, depicts a chaotic and violent incident taking place in a residential stairwell. The timestamp indicates "2025-08-17 00:35:59". Arabic text ov...

2025-10-10 14:30:25,791 - models.text_classifier - DEBUG - Sending classification request to GPT-4...
2025-10-10 14:30:28,230 - models.text_classifier - DEBUG - Raw classification result: {'crime_detected': 'YES', 'confidence_level': 'HIGH', 'type_of_crime': 'Assault', 'summary': 'Video shows violent assault in progress', 'key_evidence': ['[00:00 - 00:03] Physical violence observed', 'Distressed screams audible', 'Victim being dragged forcefully']}
2025-10-10 14:30:28,233 - models.text_classifier - DEBUG - Classification summary: Video shows violent assault in progress
```

## Error Logging Example

```
2025-10-10 14:30:15,127 - models.audio_transcriber - ERROR - Error during audio transcription: [Errno 2] No such file or directory: 'invalid_path.mp3'
Traceback (most recent call last):
  File "C:\Users\shels\Documents\wezareit el dakhleya\crime-monitoring-ai\src\models\audio_transcriber.py", line 18, in transcribe_audio
    with open(audio_path, "rb") as f:
FileNotFoundError: [Errno 2] No such file or directory: 'invalid_path.mp3'

2025-10-10 14:30:28,240 - models.aggregator - ERROR - 
============================================================
2025-10-10 14:30:28,240 - models.aggregator - ERROR - Pipeline failed after 3.45 seconds
2025-10-10 14:30:28,240 - models.aggregator - ERROR - Error: [Errno 2] No such file or directory: 'invalid_path.mp3'
2025-10-10 14:30:28,240 - models.aggregator - ERROR - 
============================================================
```

## Logged Information at Each Step

### 1. Audio Transcription
- ✅ File path being processed
- ✅ Number of segments received from API
- ✅ Total character length of transcript
- ✅ Preview of transcription (first 200 chars)
- ✅ Any errors with full stack trace

### 2. Video Captioning
- ✅ File path being processed
- ✅ Video file size (MB)
- ✅ Caption length
- ✅ Preview of caption (first 200 chars)
- ✅ Any errors with full stack trace

### 3. Crime Classification
- ✅ Raw classification result (JSON)
- ✅ Final classification: YES/NO
- ✅ Confidence level: HIGH/MEDIUM/LOW
- ✅ Type of crime identified
- ✅ Summary of decision
- ✅ Any validation or API errors

### 4. Pipeline Aggregator
- ✅ Total execution time
- ✅ Output file path
- ✅ Step-by-step progress (1/3, 2/3, 3/3)
- ✅ Success/failure status
- ✅ All errors with context

## Customizing Log Level

```python
# In main.py or your script
from logging_config import setup_logging

# For detailed debugging
setup_logging(log_level="DEBUG", log_file="debug.log")

# For production (only important info)
setup_logging(log_level="WARNING", log_file="production.log")

# For development
setup_logging(log_level="INFO", log_file="crime_monitoring.log")
```

