"""
Video analysis module using Google Gemini for detailed scene understanding.
"""

import os
import logging
from typing import Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv
import json
import asyncio

from .schemas import (
    VideoAnalysis, DetectedEntities, SceneLandmarks, PossibleCrime,
    Weapon, Vehicle, LicensePlate
)

load_dotenv()
logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """Video analysis using Google Gemini for entity detection and scene understanding."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        self.client = genai.Client(api_key=self.api_key)
    
    async def analyze_video(self, video_path: str) -> VideoAnalysis:
        """
        Analyze video for entities, landmarks, crimes, and danger assessment.
        
        Args:
            video_path: Path to video file
            
        Returns:
            VideoAnalysis object with structured results
        """
        logger.info(f"Analyzing video: {video_path}")
        
        try:
            # Read video file
            with open(video_path, 'rb') as f:
                video_bytes = f.read()
            
            video_size_mb = len(video_bytes) / (1024 * 1024)
            logger.info(f"Video size: {video_size_mb:.2f} MB")
            
            # Create detailed analysis prompt
            analysis_prompt = """Analyze this video in extreme detail and provide a comprehensive structured analysis in JSON format.

IMPORTANT: Respond ONLY with valid JSON. Do not include any explanatory text before or after the JSON.

Provide analysis in this EXACT JSON format:
{
  "description": "detailed description of what happens in the video",
  "detected_entities": {
    "weapons": [
      {"type": "weapon_type", "confidence": 0.0-1.0, "timestamp": "MM:SS", "description": "details"}
    ],
    "vehicles": [
      {
        "type": "vehicle_type",
        "color": "color",
        "license_plate": {"raw_text": "plate text", "governorate_guess": "location", "confidence": 0.0-1.0},
        "timestamp": "MM:SS"
      }
    ],
    "people_count": number,
    "other_objects": ["object1", "object2"]
  },
  "scene_landmarks": {
    "identified_landmark": "landmark name or null",
    "architectural_style": "description or null",
    "confidence": 0.0-1.0,
    "location_hints": ["hint1", "hint2"]
  },
  "possible_crimes": [
    {
      "content": "description of crime",
      "timestamp": "MM:SS",
      "rule_violated": "crime type/law violated",
      "severity": "minor/moderate/severe/critical"
    }
  ],
  "danger_score": 0-10,
  "quality_notes": "notes about video quality, lighting, clarity"
}

Guidelines:
1. **Weapons**: knife, firearm, blunt_object, sharp_object, improvised_weapon, etc.
2. **Vehicles**: sedan, suv, truck, motorcycle, etc. Include color always.
3. **License Plates**: Try to read any visible license plates. For Arabic plates, transcribe as-is.
4. **Landmarks**: Identify any recognizable locations, buildings, bridges, signs.
5. **Crimes**: assault, theft, vandalism, traffic_violation, public_disturbance, etc.
6. **Danger Score**: 0=safe, 1-3=minor concern, 4-6=moderate danger, 7-8=serious danger, 9-10=critical emergency
7. **Timestamps**: Use MM:SS format. If exact time unknown, estimate based on video position.
8. The video language is Arabic. Include any visible Arabic text.

Be thorough and precise. Only include detected items with reasonable confidence."""

            # Run analysis in thread pool since genai client is sync
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=types.Content(
                        parts=[
                            types.Part(
                                inline_data=types.Blob(data=video_bytes, mime_type='video/mp4')
                            ),
                            types.Part(text=analysis_prompt)
                        ]
                    ),
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )
            )
            
            # Parse response
            analysis_data = json.loads(response.text)
            
            # Build structured objects
            entities_data = analysis_data.get("detected_entities", {})
            
            # Parse weapons
            weapons = [
                Weapon(**w) for w in entities_data.get("weapons", [])
            ]
            
            # Parse vehicles with license plates
            vehicles = []
            for v_data in entities_data.get("vehicles", []):
                lp_data = v_data.get("license_plate")
                license_plate = None
                
                # Only create LicensePlate if we have actual data
                if lp_data and isinstance(lp_data, dict):
                    # Filter out None/null values
                    filtered_lp_data = {k: v for k, v in lp_data.items() if v is not None}
                    if filtered_lp_data:  # Only create if there's actual data
                        license_plate = LicensePlate(**filtered_lp_data)
                
                vehicle = Vehicle(
                    type=v_data.get("type", "unknown"),
                    color=v_data.get("color", "unknown"),
                    license_plate=license_plate,
                    timestamp=v_data.get("timestamp")
                )
                vehicles.append(vehicle)
            
            detected_entities = DetectedEntities(
                weapons=weapons,
                vehicles=vehicles,
                people_count=entities_data.get("people_count", 0),
                other_objects=entities_data.get("other_objects", [])
            )
            
            # Parse scene landmarks
            landmarks_data = analysis_data.get("scene_landmarks", {})
            scene_landmarks = SceneLandmarks(**landmarks_data)
            
            # Parse possible crimes
            possible_crimes = [
                PossibleCrime(**crime) for crime in analysis_data.get("possible_crimes", [])
            ]
            
            # Create final result
            result = VideoAnalysis(
                description=analysis_data.get("description", "No description available"),
                detected_entities=detected_entities,
                scene_landmarks=scene_landmarks,
                possible_crimes=possible_crimes,
                danger_score=analysis_data.get("danger_score", 5),
                quality_notes=analysis_data.get("quality_notes")
            )
            
            logger.info(
                f"✓ Video analysis complete - "
                f"Danger: {result.danger_score}/10, "
                f"Crimes: {len(possible_crimes)}, "
                f"Entities: {len(weapons)} weapons, {len(vehicles)} vehicles"
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse video analysis JSON: {str(e)}")
            logger.error(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
            raise
        except Exception as e:
            logger.error(f"Video analysis failed: {str(e)}")
            raise


# Convenience function
async def analyze_video(video_path: str) -> VideoAnalysis:
    """
    Analyze video file for entities, crimes, and danger assessment.
    
    Args:
        video_path: Path to video file
        
    Returns:
        VideoAnalysis object
    """
    analyzer = VideoAnalyzer()
    return await analyzer.analyze_video(video_path)

