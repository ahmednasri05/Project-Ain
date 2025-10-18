import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio file using OpenAI Whisper with timestamps."""
    logger.info(f"Transcribing audio: {audio_path}")
    
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        with open(audio_path, "rb") as f:
            # Get transcript with timestamp data in JSON format
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="ar",
                response_format="json",
                timestamp_granularities=["segment"]
            )
        
        # Format with timestamps if segments are available
        if hasattr(transcript, 'segments') and transcript.segments:
            lines = []
            for segment in transcript.segments:
                start = segment['start']
                end = segment['end']
                text = segment['text']
                # Format timestamps as mm:ss
                start_min, start_sec = divmod(int(start), 60)
                end_min, end_sec = divmod(int(end), 60)
                lines.append(
                    f"[{start_min:02}:{start_sec:02} - {end_min:02}:{end_sec:02}] {text}"
                )
            result = "\n".join(lines)
            logger.info(f"✓ Audio transcription complete ({len(transcript.segments)} segments)")
        else:
            # Fallback to plain text if no segments
            result = transcript.text if hasattr(transcript, 'text') else str(transcript)
            logger.info(f"✓ Audio transcription complete")
        
        return result
    
    except Exception as e:
        logger.error(f"Audio transcription failed: {str(e)}")
        raise

