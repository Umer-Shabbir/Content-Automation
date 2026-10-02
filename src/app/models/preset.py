from typing import List, Optional
from pydantic import BaseModel, Field

class TitleRules(BaseModel):
    title_structure: str = "Clear and intriguing title"
    hook_style: str = "High curiosity and tension"
    curiosity_level: int = Field(default=8, ge=1, le=10)
    forbidden_patterns: List[str] = Field(default_factory=lambda: ["Top 10", "You won't believe", "Shocking truth"])
    clickability_guidance: str = "Compelling, accurate, engaging, no misleading clickbait"
    topic_relevance: str = "Must strongly reflect the core topic without inventing a new subject"

class ScriptRules(BaseModel):
    narrative_structure: str = "Hook -> Setup -> Rising Action -> Climax -> Resolution"
    tone: str = "Atmospheric, dramatic, engaging"
    pacing: str = "Steady, building anticipation"
    target_duration_minutes: int = Field(default=10, ge=1, le=60)
    target_words: int = Field(default=1300, ge=100, le=10000)
    strict_voiceover_only: bool = Field(default=True, description="Enforce zero metadata, stage directions, or labels")

class ImageRules(BaseModel):
    visual_style: str = "Cinematic, realistic, moody lighting"
    cinematic_style: str = "Wide angles, atmospheric lighting, high detail"
    aspect_ratio: str = "16:9"
    character_consistency: str = "Preserve facial features, distinctive attire, and physical age across recurring scenes"
    environment_consistency: str = "Keep atmospheric color palette, time period, and architectural cues consistent"
    scene_density: str = "1 visual scene every 4-6 sentences"

class ReviewerRules(BaseModel):
    min_quality_score: float = Field(default=8.0, ge=1.0, le=10.0)
    max_revisions: int = Field(default=3, ge=1, le=5)
    require_voiceover_cleanliness: bool = True
    require_continuity: bool = True

class ContentPreset(BaseModel):
    id: Optional[str] = None
    name: str = Field(default="money_chuck")
    description: str = "Money Chuck house style: White-background stick-figure doodle explainers about worst business decisions, scams, and corporate collapses."
    is_builtin: bool = True
    output_dir: str = ""
    voice_name: str = Field(default="en_us_male_dry_narrator", description="Target TTS voice identifier written to metadata.json")
    title_rules: TitleRules = Field(default_factory=lambda: TitleRules(
        title_structure="Top 10 Times ONE [singular trigger] [DESTROYED/KILLED/SAVED] a [beloved entity] Explained Like You're 5",
        hook_style="Singular-agent schadenfreude: ONE decision, ONE ad, ONE mistake, ONE CEO. Caps-lock trigger verb.",
        curiosity_level=9,
        forbidden_patterns=["You won't believe", "Shocking truth", "Gone wrong", "Part 1 with no payoff", "vague nouns without a singular agent"],
        clickability_guidance="Compelling, accurate, dramatic, no misleading clickbait. Every title names a concrete singular cause and a concrete victim.",
        topic_relevance="Directly address one business-failure theme per video. All 10 stories must fit the title's promise."
    ))
    script_rules: ScriptRules = Field(default_factory=lambda: ScriptRules(
        narrative_structure="Cold-open paradox hook -> 10 self-contained mini-stories back-to-back (Peak Setup -> Fateful Decision -> Escalation -> Collapse -> Punchline kicker)",
        tone="Deadpan, wry, third-person storyteller. Dry humor, never slapstick. Mock solemnity.",
        pacing="Short punchy sentences. ~170-190 words per minute. No filler, no recap segments, no rhetorical questions.",
        target_duration_minutes=10,
        target_words=2200,
        strict_voiceover_only=True
    ))
    image_rules: ImageRules = Field(default_factory=lambda: ImageRules(
        visual_style="Minimalist black stick-figure doodle animation on a PURE WHITE background (#FFFFFF). Thick rounded marker linework, flat 2D cartoon shapes, one flat accent color max. No photorealism, no gradients, no shadows, no textures.",
        cinematic_style="Flat and simple 2D doodle style with text cards, doodle logos, and CEO caricatures.",
        aspect_ratio="16:9",
        character_consistency="One locked stick-figure design: circle head, thick rounded limbs, simple dot/dollar-sign eyes. Same linework weight.",
        environment_consistency="Background is ALWAYS pure white (#FFFFFF). No scenery, no skies, no rooms — objects float on white.",
        scene_density="1 visual prompt per 2-3 narration sentences."
    ))
    reviewer_rules: ReviewerRules = Field(default_factory=lambda: ReviewerRules(
        min_quality_score=8.5,
        max_revisions=3,
        require_voiceover_cleanliness=True,
        require_continuity=True
    ))

# Alias for compatibility with various parts of the codebase
JobPreset = ContentPreset

import json
from pathlib import Path

def load_builtin_presets() -> dict:
    registry_path = Path("H:/Automation/Presets/master_presets_registry.json")
    presets = {}
    if registry_path.exists():
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            for slug, item in data.items():
                ca = item.get("content_automation", {})
                ia = item.get("image_automation", {})
                presets[slug] = ContentPreset(
                    name=slug,
                    description=item.get("description", ""),
                    voice_name=item.get("voice_name", "en_us_male_dry_narrator"),
                    is_builtin=True,
                    title_rules=TitleRules(
                        title_structure=ca.get("title_structure", "Clear and intriguing title"),
                        hook_style=ca.get("hook_style", "High curiosity and tension"),
                        curiosity_level=9
                    ),
                    script_rules=ScriptRules(
                        narrative_structure=ca.get("narrative_structure", "Hook -> Setup -> Resolution"),
                        tone=ca.get("tone", "Atmospheric, dramatic"),
                        pacing=ca.get("pacing", "Steady, building anticipation"),
                        target_duration_minutes=ca.get("target_duration_minutes", 10),
                        target_words=ca.get("target_words", 1800),
                        strict_voiceover_only=True
                    ),
                    image_rules=ImageRules(
                        visual_style=ia.get("visual_style", "Cinematic"),
                        aspect_ratio=ia.get("aspect_ratio", "16:9"),
                        scene_density=ca.get("scene_density", "1 visual scene every 3-4 sentences")
                    ),
                    reviewer_rules=ReviewerRules(min_quality_score=8.5, max_revisions=3)
                )
        except Exception:
            pass
    if "money_chuck" not in presets:
        presets["money_chuck"] = ContentPreset()
    return presets

BUILTIN_PRESETS = load_builtin_presets()

