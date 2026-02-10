"""
Models module for crime monitoring AI.
"""

from .audio_analyzer import AudioAnalyzer, analyze_audio
from .video_analyzer import VideoAnalyzer, analyze_video
from .media_processor import MediaProcessor, process_media
from .schemas import (
    AudioAnalysis,
    AudioEvent,
    VideoAnalysis,
    DetectedEntities,
    SceneLandmarks,
    PossibleCrime,
    Weapon,
    Vehicle,
    LicensePlate,
    MediaAnalysisResult
)

__all__ = [
    # Analyzers
    'AudioAnalyzer',
    'VideoAnalyzer',
    'MediaProcessor',
    # Functions
    'analyze_audio',
    'analyze_video',
    'process_media',
    # Schemas
    'AudioAnalysis',
    'AudioEvent',
    'VideoAnalysis',
    'DetectedEntities',
    'SceneLandmarks',
    'PossibleCrime',
    'Weapon',
    'Vehicle',
    'LicensePlate',
    'MediaAnalysisResult',
]

