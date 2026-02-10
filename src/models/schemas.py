"""
Pydantic schemas for structured video and audio analysis outputs.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# Audio Analysis Schemas
class AudioEvent(BaseModel):
    """Detected audio event."""
    event: str = Field(..., description="Type of audio event (e.g., glass_shattering, aggressive_shouting)")
    timestamp: str = Field(..., description="Timestamp in format MM:SS")
    intensity: Optional[str] = Field(None, description="Intensity level (low, medium, high)")


class AudioAnalysis(BaseModel):
    """Complete audio analysis results."""
    transcript: str = Field(..., description="Full transcription of audio")
    audio_events: List[AudioEvent] = Field(default_factory=list, description="Detected audio events")
    sentiment: str = Field(..., description="Overall sentiment (e.g., Distress/Aggression, Calm, Neutral)")
    language: str = Field(default="ar", description="Detected language")
    confidence: float = Field(default=0.0, description="Overall confidence score")


# Video Analysis Schemas
class Weapon(BaseModel):
    """Detected weapon."""
    type: str = Field(..., description="Type of weapon (e.g., blunt_object, knife, firearm)")
    confidence: float = Field(..., description="Detection confidence (0-1)")
    timestamp: str = Field(..., description="Timestamp in format MM:SS")
    description: Optional[str] = Field(None, description="Additional description")


class LicensePlate(BaseModel):
    """License plate information."""
    raw_text: Optional[str] = Field(None, description="Raw text from license plate")
    governorate_guess: Optional[str] = Field(None, description="Guessed governorate/region")
    confidence: Optional[float] = Field(None, description="OCR confidence (0-1)")


class Vehicle(BaseModel):
    """Detected vehicle."""
    type: str = Field(..., description="Type of vehicle (e.g., sedan, suv, motorcycle)")
    color: str = Field(..., description="Vehicle color")
    license_plate: Optional[LicensePlate] = Field(None, description="License plate data if visible")
    timestamp: Optional[str] = Field(None, description="First appearance timestamp")


class DetectedEntities(BaseModel):
    """All detected entities in video."""
    weapons: List[Weapon] = Field(default_factory=list)
    vehicles: List[Vehicle] = Field(default_factory=list)
    people_count: int = Field(default=0, description="Number of people detected")
    other_objects: List[str] = Field(default_factory=list, description="Other notable objects")


class SceneLandmarks(BaseModel):
    """Identified scene landmarks and location info."""
    identified_landmark: Optional[str] = Field(None, description="Recognized landmark name")
    architectural_style: Optional[str] = Field(None, description="Architectural style or area description")
    confidence: float = Field(default=0.0, description="Landmark identification confidence")
    location_hints: List[str] = Field(default_factory=list, description="Other location clues")


class PossibleCrime(BaseModel):
    """Detected possible crime."""
    content: str = Field(..., description="Description of the crime")
    timestamp: str = Field(..., description="Timestamp in format MM:SS")
    rule_violated: str = Field(..., description="Legal rule or crime type")
    severity: str = Field(..., description="Severity level (minor, moderate, severe, critical)")


class VideoAnalysis(BaseModel):
    """Complete video analysis results."""
    description: str = Field(..., description="Overall description of video content")
    detected_entities: DetectedEntities = Field(default_factory=DetectedEntities)
    scene_landmarks: SceneLandmarks = Field(default_factory=SceneLandmarks)
    possible_crimes: List[PossibleCrime] = Field(default_factory=list)
    danger_score: int = Field(..., ge=0, le=10, description="Overall danger score (0-10)")
    quality_notes: Optional[str] = Field(None, description="Notes about video quality")


# Combined Analysis Result
class MediaAnalysisResult(BaseModel):
    """Complete media analysis combining video and audio."""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    video_path: str
    audio_path: Optional[str] = None
    video_analysis: VideoAnalysis
    audio_analysis: AudioAnalysis
    overall_assessment: str = Field(..., description="Combined assessment of the situation")
    recommended_action: Optional[str] = Field(None, description="Recommended action based on analysis")


# Sentiment Analysis Schemas
class SentimentAnalysis(BaseModel):
    """Sentiment analysis results."""
    label: str = Field(..., description="Sentiment label (CRIME_REPORT, SPAM_SARCASM, AMBIGUOUS)")
    explanation: str = Field(..., description="Explanation for the sentiment label")
