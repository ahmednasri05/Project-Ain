"""
Models module for crime monitoring AI.
"""

from .audio_analyzer import AudioAnalyzer, analyze_audio
from .video_analyzer import VideoAnalyzer, analyze_video
from .media_processor import MediaProcessor, process_media
from .embedding import embed_texts
from .sentiment_analyzer import SentimentAnalyzer
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
    MediaAnalysisResult,
    SentimentAnalysis,
    PenalCodeArticle,
)


__all__ = [
    # Analyzers
    'AudioAnalyzer',
    'VideoAnalyzer',
    'MediaProcessor',
    'SentimentAnalyzer',
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
    'SentimentAnalysis',
    'PenalCodeArticle',
    'embed_texts',
]

