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
        
        # Try-except block required: move all logic inside the try block so there is at least one except or finally for each try.
        try:
            # Read video file
            with open(video_path, 'rb') as f:
                video_bytes = f.read()
            
            video_size_mb = len(video_bytes) / (1024 * 1024)
            logger.info(f"Video size: {video_size_mb:.2f} MB")
            
            # Create detailed analysis prompt
            analysis_prompt = """You are a Senior Forensic Investigator for the Egyptian Public Prosecution’s Digital Evidence Unit.
             Your objective is to classify video content for potential violations of the Egyptian Penal Code, Traffic Law, and Cybercrime Law or other crimes in general. 
             You must first verify if the video occurs within Egypt otherwise irrelevant. you must distinguish between actionable crimes and social media spam.
              Any video identified as an action movie clip, video game footage, viral prank, fictional content,
               or violence occurring outside of Egypt is IRRELEVANT.

IMPORTANT: Respond ONLY with valid JSON. Do not include any explanatory text before or after the JSON.

Provide analysis in this EXACT JSON format:
{
  "description": "detailed description of what happens in the video",
  # ONLY include relevant entities to crime detection
  "detected_entities": {
    "weapons": [
      {"type": "weapon_type", "confidence": 0.0-1.0, "timestamp": "MM:SS", "description": "details"}
    ],
    #ONLY include if relevant to crime detection:
    "vehicles": [
      {
        "type": "vehicle_type",
        "color": "color",
        "license_plate": {"raw_text": "plate text", "governorate_guess": "location", "confidence": 0.0-1.0},
        "timestamp": "MM:SS"
      }
    ],
    "people_count": number,
    #other objects relevant to crime detection
    "other_objects": ["object1", "object2"]
  },
  "scene_landmarks": {
    "identified_landmark": "landmark name or null",
    "architectural_style": "description or null",
    "approximate_location": "predicted location (city, district, street) or null",
    "confidence": 0.0-1.0,
    "location_hints": ["hint1", "hint2"]
  },
  "possible_crimes": [
    {
      "content": "description of crime",
      "timestamp": "MM:SS",
      "rule_violated": "short crime label",
      "severity": "minor/moderate/severe/critical",
      "penal_code_query": "formal Egyptian Penal Code characterisation for semantic search"
    }
  ],
  "danger_score": 0,
  "crime_classification": "جناية",
  "crime_category": [1, 4],
  "in_egypt": "نعم"
}

CRIME CATEGORY REFERENCE (choose up to 2 numbers):
1. أعمال العنف والمشاجرات
2. أعمال البلطجة وترويع المواطنين
3. الاستخدام غير القانوني للأسلحة
4. الجرائم المرورية وتعريض الأرواح للخطر
5. التعدي على الآداب والقيم العامة
6. السرقة والنشل والسطو
7. تعاطي أو ترويج المواد المخدرة علناً
8. التحرش الجسدي واللفظي
9. لا شيء
10. اخري",
  "in_egypt": "نعم" | "لا" | "غير محدد"
}

Guidelines:
1. **Weapons**: knife, firearm, blunt_object, sharp_object, improvised_weapon, etc.
2. **Vehicles**: sedan, suv, truck, motorcycle, etc. Include color always.
3. **License Plates**: Try to read any visible license plates. For Arabic plates, transcribe as-is.
4. **Landmarks**: Identify any recognizable locations, buildings, bridges, signs, streets.
5. **Approximate Location**: Based on landmarks, signs, architecture, license plates, and any visible text, language, predict the most specific location possible. Format: "City, District, Street" or "City, Area description". Include Egyptian governorate if in Egypt only if you are sure. Be as detailed and accurate as possible.
6. **Crimes** — two separate fields per crime:
   - `rule_violated`: a short Arabic display label, e.g. "ضرب وجرح بسلاح", "سرقة بالإكراه", "إتلاف ممتلكات".
   - `penal_code_query`: 1–2 sentences in formal legal Arabic characterising the offense for semantic search against قانون العقوبات المصري. Include: the precise legal act (e.g. إيذاء جسدي عمد، سرقة بالتهديد), any aggravating circumstances visible (استخدام سلاح، تعدد الجناة، الليل), the punishment tier implied (جناية/جنحة/مخالفة), and any relevant legal concepts (إكراه، عاهة مستديمة، تلبّس). Example: "إيذاء جسدي عمدي بالضرب باستخدام آلة حادة أفضى إلى جرح — جريمة ضرب وجرح وفقاً لأحكام قانون العقوبات المصري، مع توافر ظرف مشدد لاستخدام سلاح."
7. **Danger Score**: 0=safe, 1-3=violation, 4-6=misdemeanor, 7-10=felony. Align with crime_classification below!
8. **Timestamps**: Use MM:SS format. If exact time unknown, estimate based on video position.
9. **Location**: Set "in_egypt" to exactly one of these three values based on visual evidence (landmarks, license plates, signage, architecture, language of text visible in video):
    - "نعم"       → clear evidence the crime takes place in Egypt.
    - "لا"        → clear evidence the crime takes place outside Egypt.
    - "غير محدد"  → insufficient visual evidence to determine location. Use this when unsure — do NOT guess.
    Score and classification always reflect the crime's true severity regardless of location.
10. **Crime Classification** (Egyptian Penal Code): Choose exactly one:
    - "جناية"  → felony: punishable by imprisonment ≥ 3 years or death (e.g. murder, armed assault, rape, armed robbery). Danger score 7-10.
    - "جنحة"   → misdemeanor: punishable by imprisonment < 3 years or fine (e.g. assault, theft, vandalism, public disturbance). Danger score 4-6.
    - "مخالفة" → violation: minor infraction punishable by fine only (e.g. traffic violation, littering, noise). Danger score 1-3.
    - "لا شيء" → no crime detected. Danger score 0.

Be thorough and precise. Only include detected items with reasonable confidence. For location prediction, use all available visual clues including:
- Recognizable landmarks (mosques, bridges, buildings)
- Street signs and store names
- License plate patterns (Egyptian governorate codes)
- Architectural style (modern Cairo, old district, coastal, etc.)
- Environmental features (Nile river, desert, urban density)

LANGUAGE REQUIREMENT: Write ALL text values in Arabic (Modern Standard Arabic / Egyptian Arabic). This includes: description, weapon descriptions, other_objects items, identified_landmark, architectural_style, approximate_location, location_hints items, crime content, rule_violated, penal_code_query, and quality_notes. EXCEPTION: Keep severity values strictly as one of these English words: minor / moderate / severe / critical. Keep timestamp format as MM:SS.
"""
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
            # Normalize crime_category: ensure it's a list of ints clamped to 1-10
            raw_category = analysis_data.get("crime_category", [])
            if isinstance(raw_category, int):
                raw_category = [raw_category]
            crime_category = [c for c in raw_category if isinstance(c, int) and 1 <= c <= 10][:2]

            result = VideoAnalysis(
                description=analysis_data.get("description", "No description available"),
                detected_entities=detected_entities,
                scene_landmarks=scene_landmarks,
                possible_crimes=possible_crimes,
                danger_score=analysis_data.get("danger_score", 5),
                crime_classification=analysis_data.get("crime_classification"),
                crime_category=crime_category,
                in_egypt=analysis_data.get("in_egypt", "غير محدد"),
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

