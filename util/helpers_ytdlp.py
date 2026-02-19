"""
Alternative download using yt-dlp (more robust for Instagram)
Install: pip install yt-dlp
"""
import os
import asyncio
import yt_dlp
from moviepy import VideoFileClip

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  
SAVE_DIR = os.path.join(BASE_DIR, "downloads")


async def download_video_ytdlp(media_url: str, media_id: str):
    """Download video using yt-dlp (handles Instagram authentication)"""
    os.makedirs(SAVE_DIR, exist_ok=True)
    filepath = os.path.join(SAVE_DIR, f"{media_id}.mp4")
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': filepath,
        'quiet': True,
        'no_warnings': True,
    }
    
    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([media_url])
    
    # Run in thread to avoid blocking async event loop
    await asyncio.to_thread(_download)
    
    return filepath


async def extract_audio(video_path: str, filename: str, save_dir: str = SAVE_DIR):
    audio_path = os.path.join(save_dir, f"{filename}.mp3")
    clip = VideoFileClip(video_path)
    await asyncio.to_thread(clip.audio.write_audiofile, audio_path)
    clip.close()
    return audio_path
