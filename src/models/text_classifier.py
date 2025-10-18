import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Literal

load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

class CrimeClassification(BaseModel):
    """Pydantic model for crime classification output."""
    crime_detected: Literal["YES", "NO"] = Field(description="Whether crime was detected")
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"] = Field(description="Confidence level of detection")
    type_of_crime: str = Field(description="Type of crime detected, or 'N/A' if none")
    summary: str = Field(description="Brief explanation of the decision")
    key_evidence: List[str] = Field(description="List of key evidence supporting the conclusion")
    

# should include egyptian rules and compare to them in future!!
def classify_crime(audio_transcript: str, video_caption: str) -> CrimeClassification:
    """Classify if content contains criminal activity with structured output."""
    logger.info("Classifying content for crimes...")
    
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""You are a crime detection AI. Analyze the following audio transcript and video description to determine if they contain or suggest criminal activity.

Audio Transcript:
{audio_transcript}

Video Description:
{video_caption}

Respond with a JSON object in this exact format:
{{
    "crime_detected": "YES" or "NO",
    "confidence_level": "HIGH" or "MEDIUM" or "LOW",
    "type_of_crime": "type of crime or N/A if none",
    "summary": "brief explanation of your decision",
    "key_evidence": ["list", "of", "key", "phrases", "timestamps", "or", "observations"]
}}
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert crime analyst. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Parse and validate with Pydantic
        result_dict = json.loads(response.choices[0].message.content)
        classification = CrimeClassification(**result_dict)
        
        logger.info(f"✓ Classification: {classification.crime_detected} | "
                   f"Confidence: {classification.confidence_level} | "
                   f"Type: {classification.type_of_crime}")
        
        return classification
    
    except Exception as e:
        logger.error(f"Crime classification failed: {str(e)}")
        raise

