import json
import os
import logging
from pathlib import Path
from datetime import datetime
from .audio_transcriber import transcribe_audio
from .video_captioner import caption_video
from .text_classifier import classify_crime

# Configure logger
logger = logging.getLogger(__name__)

def process_video(video_path: str, audio_path: str = None, output_dir: str = "output") -> dict:
    """
    Process video and audio, classify for crimes, and save results.
    
    Args:
        video_path: Path to video file (mp4)
        audio_path: Path to audio file (mp3). If None, assumes same name as video
        output_dir: Directory to save results
    
    Returns:
        dict: Processing results
    """
    logger.info("="*60)
    logger.info("CRIME MONITORING PIPELINE - STARTED")
    logger.info("="*60)
    
    start_time = datetime.now()
    
    try:
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # If no audio path provided, assume it's extracted from video with same name
        if audio_path is None:
            audio_path = str(Path(video_path).with_suffix('.mp3'))
        
        # Step 1: Audio Transcription
        logger.info("[1/3] Audio Transcription")
        audio_transcript = transcribe_audio(audio_path)
        
        # Step 2: Video Captioning
        logger.info("[2/3] Video Captioning")
        video_caption = caption_video(video_path)
        
        # Step 3: Crime Classification
        logger.info("[3/3] Crime Classification")
        classification = classify_crime(audio_transcript, video_caption)
        
        # Prepare results
        results = {
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "audio_path": audio_path,
            "audio_transcript": audio_transcript,
            "video_caption": video_caption,
            "crime_classification": classification.model_dump()  # Convert Pydantic model to dict
        }
        
        # Save to JSON
        output_file = output_path / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        logger.info("="*60)
        logger.info(f"PIPELINE COMPLETE - {elapsed_time:.2f}s")
        logger.info(f"Output: {output_file}")
        logger.info("="*60)
        
        return results
    
    except Exception as e:
        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.error("="*60)
        logger.error(f"PIPELINE FAILED - {elapsed_time:.2f}s")
        logger.error(f"Error: {str(e)}")
        logger.error("="*60)
        raise

