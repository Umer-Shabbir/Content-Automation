from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class ScenePrompt(BaseModel):
    scene_number: int
    narration_segment: str
    start_time: str = ""
    end_time: str = ""
    visual_description: str
    characters_present: List[str] = Field(default_factory=list)
    location: str = ""
    mood_lighting: str = ""
    camera_angle: str = ""
    detailed_image_prompt: str

class VisualContinuityState(BaseModel):
    recurring_characters: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of character name to locked physical description"
    )
    recurring_locations: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of location name to locked environmental and architectural description"
    )
    art_style_anchor: str = ""

class GenerationPackage(BaseModel):
    topic: str
    preset_name: str
    voice_name: str = "Adam   ·  American Male"
    video_language: str = "English"
    title: str
    normalized_title: str
    seo_tags: List[str] = Field(default_factory=list)
    seo_description: str = ""
    script: str
    prompts: List[ScenePrompt]
    continuity: VisualContinuityState = Field(default_factory=VisualContinuityState)
    thumbnail_prompts: List[str] = Field(default_factory=list)
    total_words: int = 0
    estimated_duration_sec: float = 0.0
    quality_score: float = 0.0
    reviewer_notes: Optional[str] = None
