# Location Prediction Feature

## Overview

The video analysis pipeline now includes **approximate location prediction** based on visual clues in the video content. This feature uses landmarks, signs, architecture, license plates, and environmental features to predict the most specific location possible.

## Schema Update

### `SceneLandmarks` Model

Added new field: `approximate_location`

```python
class SceneLandmarks(BaseModel):
    """Identified scene landmarks and location info."""
    identified_landmark: Optional[str]        # e.g., "Cairo Tower"
    architectural_style: Optional[str]        # e.g., "Modern high-rise district"
    approximate_location: Optional[str]       # NEW: "Cairo, Zamalek, 26th of July Street"
    confidence: float                         # 0.0-1.0
    location_hints: List[str]                 # ["Nile view", "Metro sign visible"]
```

## How It Works

The video analyzer uses multiple visual clues to predict location:

### 1. **Recognizable Landmarks**
- Famous buildings (Cairo Tower, Citadel, etc.)
- Bridges (6th October Bridge, Qasr El Nil Bridge)
- Monuments and historical sites
- Shopping centers and known venues

### 2. **Street Signs & Text**
- Street name signs (Arabic/English)
- Store names and shop fronts
- Metro station signs
- Government building signs

### 3. **License Plates**
- Egyptian governorate codes
- Plate patterns and formats
- Regional variations

### 4. **Architectural Style**
- Modern Cairo (New Cairo, Sheikh Zayed)
- Old Cairo (Islamic Cairo, Coptic Cairo)
- Coastal areas (Alexandria, Mediterranean style)
- Desert development areas

### 5. **Environmental Features**
- Nile River visibility
- Urban density patterns
- Vegetation and climate indicators
- Coastal vs. inland characteristics

## Location Format

The `approximate_location` field follows this hierarchical format:

```
"Governorate/City, District/Area, Street/Specific Location"
```

### Examples:

**High Confidence (Specific):**
```
"Cairo, Zamalek, 26th of July Street near Cairo Tower"
"Alexandria, Smouha, Mostafa Kamel Street"
"Giza, 6th of October City, Mall of Arabia area"
```

**Medium Confidence (District):**
```
"Cairo, Downtown area"
"Cairo, Heliopolis district"
"Giza, Dokki neighborhood"
```

**Low Confidence (City):**
```
"Cairo, urban area"
"Alexandria, coastal zone"
"Unknown Egyptian city"
```

**Unknown:**
```
null  // When no location clues are available
```

## Usage

### Example Analysis Output

```json
{
  "scene_landmarks": {
    "identified_landmark": "Cairo Tower",
    "architectural_style": "Modern high-rise area with Nile view",
    "approximate_location": "Cairo, Zamalek, 26th of July Street",
    "confidence": 0.9,
    "location_hints": [
      "Nile River visible",
      "Cairo Tower in background",
      "Modern bridge structure",
      "Arabic street signs visible"
    ]
  }
}
```

### In Media Processor Output

The location is now included in:

1. **Video Analysis Results**
2. **Overall Assessment** (automatically mentions location if detected)
3. **Log Output** (shows location in pipeline summary)

### Example Log Output:

```
==============================================================
PIPELINE COMPLETE - 15.43s
Danger Score: 7/10
Crimes Detected: 2
Audio Events: 3
Location: Cairo, Downtown, Tahrir Square area
Output: output/media_analysis_20260216_143052.json
==============================================================
```

## Integration with Overall Assessment

The location context is automatically included in the AI-generated assessment:

```python
# Before (without location):
"Video shows aggressive confrontation with weapons visible. Danger level: 7/10. 
Audio indicates distress and aggressive shouting."

# After (with location):
"Video shows aggressive confrontation with weapons visible in Cairo, Downtown area. 
Danger level: 7/10. Audio indicates distress and aggressive shouting. 
Location identified near Tahrir Square based on visible landmarks."
```

## API Usage

### Accessing Location in Code

```python
from src.models import process_media

# Run analysis
result = await process_media(video_path, audio_path)

# Access location
location = result.video_analysis.scene_landmarks.approximate_location

if location:
    print(f"Incident location: {location}")
    confidence = result.video_analysis.scene_landmarks.confidence
    print(f"Confidence: {confidence * 100:.1f}%")
    
    # Get additional hints
    hints = result.video_analysis.scene_landmarks.location_hints
    print(f"Supporting clues: {', '.join(hints)}")
```

### Example with Crime Detection

```python
result = await process_media(video_path, audio_path)

if result.video_analysis.danger_score >= 7:
    location = result.video_analysis.scene_landmarks.approximate_location
    
    alert = {
        "danger_level": result.video_analysis.danger_score,
        "location": location or "Unknown",
        "crimes": [c.content for c in result.video_analysis.possible_crimes],
        "timestamp": result.timestamp
    }
    
    # Send to authorities with location info
    await send_emergency_alert(alert)
```

## Benefits

✅ **Faster Response** - Authorities know where to go immediately  
✅ **Evidence Correlation** - Link incidents to specific locations  
✅ **Pattern Detection** - Identify high-crime areas  
✅ **Resource Allocation** - Deploy resources to correct locations  
✅ **Verification** - Cross-reference with other location data  

## Accuracy Considerations

### High Accuracy (0.8-1.0)
- Famous landmarks clearly visible
- Street signs readable
- Multiple corroborating clues

### Medium Accuracy (0.5-0.8)
- Architectural style identified
- General area recognizable
- Some location hints present

### Low Accuracy (0.0-0.5)
- Generic urban environment
- Few distinctive features
- Ambiguous clues

## Use Cases

### 1. Emergency Response
```python
if danger_score >= 8 and approximate_location:
    dispatch_police(location=approximate_location)
```

### 2. Crime Mapping
```python
crime_map.add_incident(
    location=approximate_location,
    type=crime_type,
    severity=danger_score
)
```

### 3. Statistical Analysis
```python
# Group crimes by location
location_stats = group_by_location(all_incidents)
hotspots = identify_hotspots(location_stats)
```

### 4. Evidence Management
```python
incident_report = {
    "video_path": video_path,
    "location": approximate_location,
    "witnesses": extract_from_comments(shortcode),
    "timestamp": posted_at
}
```

## Future Enhancements

🔮 **Potential Improvements:**
- GPS coordinate prediction
- Real-time location verification via maps API
- Historical incident correlation
- Multi-video location triangulation
- Integration with Egyptian governorate databases

---

## Technical Details

**Model Used:** Google Gemini 2.5 Flash  
**Context Window:** Entire video analyzed  
**Response Format:** Structured JSON with location field  
**Language Support:** Arabic and English text recognition  
**Regional Focus:** Egyptian locations and landmarks  

