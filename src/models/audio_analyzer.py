"""
Audio transcription and analysis module using OpenAI Whisper.
"""

import os
import logging
from typing import Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
import json

from .schemas import AudioAnalysis, AudioEvent

load_dotenv()
logger = logging.getLogger(__name__)


class AudioAnalyzer:
    """Audio transcription and analysis using OpenAI Whisper and GPT."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def transcribe_audio(self, audio_path: str, language: str = "ar") -> str:
        """
        Transcribe audio file using OpenAI Whisper.
        
        Args:
            audio_path: Path to audio file
            language: Language code (default: "ar" for Arabic)
            
        Returns:
            Transcribed text with timestamps
        """
        logger.info(f"Transcribing audio: {audio_path}")
        
        try:
            with open(audio_path, "rb") as f:
                # Get transcript with timestamp data
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language=language,
                    response_format="verbose_json",  # Get detailed info with timestamps
                    timestamp_granularities=["segment"]
                )
            
            # Format transcript with timestamps if available
            if hasattr(transcript, 'segments') and transcript.segments:
                lines = []
                for segment in transcript.segments:
                    # Segments are objects, not dicts - access attributes directly
                    start = getattr(segment, 'start', 0)
                    end = getattr(segment, 'end', 0)
                    text = getattr(segment, 'text', '')
                    
                    # Format timestamps as MM:SS
                    start_min, start_sec = divmod(int(start), 60)
                    end_min, end_sec = divmod(int(end), 60)
                    lines.append(
                        f"[{start_min:02}:{start_sec:02} - {end_min:02}:{end_sec:02}] {text}"
                    )
                result = "\n".join(lines)
                logger.info(f"✓ Audio transcription complete ({len(transcript.segments)} segments)")
            else:
                # Fallback to plain text
                result = transcript.text if hasattr(transcript, 'text') else str(transcript)
                logger.info("✓ Audio transcription complete")
            
            return result
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {str(e)}")
            raise
    
    async def analyze_audio(self, audio_path: str, language: str = "ar") -> AudioAnalysis:
        """
        Transcribe and analyze audio for events, sentiment, and content.
        
        Args:
            audio_path: Path to audio file
            language: Language code
            
        Returns:
            AudioAnalysis object with structured results
        """
        logger.info(f"Analyzing audio: {audio_path}")
        
        try:
            # Step 1: Transcribe audio
            transcript = await self.transcribe_audio(audio_path, language)
            
            # Step 2: Analyze with GPT for events and sentiment
            analysis_prompt = f"""Analyze this audio transcript and provide a structured analysis in JSON format.

Transcript:
{transcript}

Provide analysis in this EXACT JSON format:
{{
  "audio_events": [
    {{"event": "event_type", "timestamp": "MM:SS", "intensity": "low/medium/high"}}
  ],
  "sentiment": "overall sentiment description",
  "language": "detected language code",
  "confidence": 0.0-1.0
}}

Audio events to detect:
- glass_shattering, aggressive_shouting, screaming, crying, gunshot, 
- car_crash, alarm, door_breaking, running_footsteps, physical_altercation
- Any other significant audio events

Sentiment categories:
- Distress/Aggression, Panic/Fear, Anger, Calm, Neutral, Confusion

Only include events that are clearly audible. Be precise with timestamps."""

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert audio forensic analyst. Analyze audio transcripts to detect events, sentiment, and important details. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            analysis_data = json.loads(response.choices[0].message.content)
            
            # Parse audio events
            audio_events = [
                AudioEvent(**event) for event in analysis_data.get("audio_events", [])
            ]
            
            result = AudioAnalysis(
                transcript=transcript,
                audio_events=audio_events,
                sentiment=analysis_data.get("sentiment", "Neutral"),
                language=analysis_data.get("language", language),
                confidence=analysis_data.get("confidence", 0.8)
            )
            
            logger.info(f"✓ Audio analysis complete - {len(audio_events)} events detected")
            return result
            
        except Exception as e:
            logger.error(f"Audio analysis failed: {str(e)}")
            raise


# Convenience function for backward compatibility
async def analyze_audio(audio_path: str, language: str = "ar") -> AudioAnalysis:
    """
    Analyze audio file (transcribe + analyze events/sentiment).
    
    Args:
        audio_path: Path to audio file
        language: Language code
        
    Returns:
        AudioAnalysis object
    """
    analyzer = AudioAnalyzer()
    return await analyzer.analyze_audio(audio_path, language)

