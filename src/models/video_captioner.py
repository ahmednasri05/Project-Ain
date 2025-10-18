import os
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

def caption_video(video_path: str) -> str:
    """Generate detailed caption for video using Gemini."""
    logger.info(f"Captioning video: {video_path}")
    
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        with open(video_path, 'rb') as f:
            video_bytes = f.read()
        
        video_size_mb = len(video_bytes) / (1024 * 1024)
        logger.info(f"Video size: {video_size_mb:.2f} MB")
        
        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=types.Content(
                parts=[
                    types.Part(
                        inline_data=types.Blob(data=video_bytes, mime_type='video/mp4')
                    ),
                    types.Part(text='Give a detailed description of the video and what happens in it. The language of the video is Arabic. the description should include timestamps.')
                ]
            )
        )
        
        caption = response.text
        logger.info(f"✓ Video captioning complete")
        
        return caption
    
    except Exception as e:
        logger.error(f"Video captioning failed: {str(e)}")
        raise

