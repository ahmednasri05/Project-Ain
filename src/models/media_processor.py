"""
Integrated media processor combining audio and video analysis.
Uses async processing for parallel execution.
"""

import os
import logging
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from .audio_analyzer import AudioAnalyzer
from .video_analyzer import VideoAnalyzer
from .schemas import MediaAnalysisResult, AudioAnalysis, VideoAnalysis

logger = logging.getLogger(__name__)


class MediaProcessor:
    """
    Integrated media processor that orchestrates parallel audio and video analysis.
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None
    ):
        """
        Initialize with API keys.
        
        Args:
            openai_api_key: OpenAI API key (if None, reads from env)
            gemini_api_key: Google Gemini API key (if None, reads from env)
        """
        self.audio_analyzer = AudioAnalyzer(api_key=openai_api_key)
        self.video_analyzer = VideoAnalyzer(api_key=gemini_api_key)
    
    async def process_media(
        self,
        video_path: str,
        audio_path: Optional[str] = None,
        output_dir: str = "output",
        language: str = "ar"
    ) -> MediaAnalysisResult:
        """
        Process video and audio files with parallel analysis.
        
        Args:
            video_path: Path to video file
            audio_path: Path to audio file (if None, assumes same name as video with .mp3)
            output_dir: Directory to save results
            language: Audio language code
            
        Returns:
            MediaAnalysisResult with complete analysis
        """
        logger.info("="*60)
        logger.info("MEDIA ANALYSIS PIPELINE - STARTED")
        logger.info("="*60)
        
        start_time = datetime.now()
        
        try:
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # If no audio path provided, assume it's extracted with same name
            if audio_path is None:
                audio_path = str(Path(video_path).with_suffix('.mp3'))
            
            logger.info(f"Video: {video_path}")
            logger.info(f"Audio: {audio_path}")
            
            # Run audio and video analysis in parallel
            logger.info("Starting parallel analysis...")
            
            audio_task = asyncio.create_task(
                self._analyze_audio_safe(audio_path, language)
            )
            video_task = asyncio.create_task(
                self._analyze_video_safe(video_path)
            )
            
            # Wait for both to complete
            audio_analysis, video_analysis = await asyncio.gather(
                audio_task,
                video_task
            )
            
            # Generate overall assessment
            logger.info("Generating combined assessment...")
            overall_assessment = await self._generate_assessment(
                video_analysis,
                audio_analysis
            )

            # Build final result
            result = MediaAnalysisResult(
                video_path=video_path,
                audio_path=audio_path,
                video_analysis=video_analysis,
                audio_analysis=audio_analysis,
                overall_assessment=overall_assessment
            )
            
            # Save to JSON
            output_file = output_path / f"media_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            logger.info("="*60)
            logger.info(f"PIPELINE COMPLETE - {elapsed_time:.2f}s")
            logger.info(f"Danger Score: {video_analysis.danger_score}/10")
            logger.info(f"Crimes Detected: {len(video_analysis.possible_crimes)}")
            logger.info(f"Audio Events: {len(audio_analysis.audio_events)}")
            logger.info(f"Output: {output_file}")
            logger.info("="*60)
            
            return result
            
        except Exception as e:
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.error("="*60)
            logger.error(f"PIPELINE FAILED - {elapsed_time:.2f}s")
            logger.error(f"Error: {str(e)}")
            logger.error("="*60)
            raise
    
    async def _analyze_audio_safe(self, audio_path: str, language: str) -> AudioAnalysis:
        """Safely analyze audio with error handling."""
        try:
            if not os.path.exists(audio_path):
                logger.warning(f"Audio file not found: {audio_path}")
                # Return empty analysis if audio not available
                from .schemas import AudioAnalysis
                return AudioAnalysis(
                    transcript="[Audio file not available]",
                    audio_events=[],
                    sentiment="Unknown",
                    language=language,
                    confidence=0.0
                )
            
            logger.info("[1/2] Analyzing audio...")
            result = await self.audio_analyzer.analyze_audio(audio_path, language)
            logger.info(f"✓ Audio analysis complete")
            return result
            
        except Exception as e:
            logger.error(f"Audio analysis failed: {str(e)}")
            # Return minimal analysis on error
            from .schemas import AudioAnalysis
            return AudioAnalysis(
                transcript=f"[Error: {str(e)}]",
                audio_events=[],
                sentiment="Error",
                language=language,
                confidence=0.0
            )
    
    async def _analyze_video_safe(self, video_path: str) -> VideoAnalysis:
        """Safely analyze video with error handling."""
        try:
            logger.info("[2/2] Analyzing video...")
            result = await self.video_analyzer.analyze_video(video_path)
            logger.info(f"✓ Video analysis complete")
            return result
            
        except Exception as e:
            logger.error(f"Video analysis failed: {str(e)}")
            raise  # Video analysis is critical, so we raise
    
    async def _generate_assessment(
        self,
        video_analysis: VideoAnalysis,
        audio_analysis: AudioAnalysis
    ) -> str:
        """
        Generate overall assessment combining video and audio analysis.
        
        Args:
            video_analysis: Video analysis results
            audio_analysis: Audio analysis results
            
        Returns:
            Overall assessment string
        """
        # Use OpenAI to generate a coherent assessment
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.audio_analyzer.api_key)
            
            assessment_prompt = f"""Based on the following video and audio analysis, provide a comprehensive overall assessment of the situation:

VIDEO ANALYSIS:
- Description: {video_analysis.description}
- Danger Score: {video_analysis.danger_score}/10
- Detected Crimes: {len(video_analysis.possible_crimes)}
- People Count: {video_analysis.detected_entities.people_count}
- Weapons: {len(video_analysis.detected_entities.weapons)}
- Vehicles: {len(video_analysis.detected_entities.vehicles)}

AUDIO ANALYSIS:
- Transcript: {audio_analysis.transcript[:500]}...
- Sentiment: {audio_analysis.sentiment}
- Audio Events: {len(audio_analysis.audio_events)}

Provide a 2-3 sentence assessment that summarizes:
1. What is happening
2. The level of danger/concern
3. Key evidence from both video and audio"""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a crime analysis expert. Provide clear, concise assessments."},
                    {"role": "user", "content": assessment_prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.warning(f"Failed to generate AI assessment: {str(e)}")
            # Fallback to simple assessment
            return (
                f"Video shows {video_analysis.description[:100]}. "
                f"Danger level: {video_analysis.danger_score}/10. "
                f"Audio sentiment: {audio_analysis.sentiment}."
            )
    

# Convenience function
async def process_media(
    video_path: str,
    audio_path: Optional[str] = None,
    output_dir: str = "output",
    language: str = "ar"
) -> MediaAnalysisResult:
    """
    Process media files with parallel audio and video analysis.
    
    Args:
        video_path: Path to video file
        audio_path: Path to audio file (optional)
        output_dir: Output directory for results
        language: Audio language code
        
    Returns:
        MediaAnalysisResult with complete analysis
    """
    processor = MediaProcessor()
    return await processor.process_media(video_path, audio_path, output_dir, language)

