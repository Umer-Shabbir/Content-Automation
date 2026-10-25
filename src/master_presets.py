import json
from pathlib import Path

REGISTRY_PATH = Path("H:/Automation/Presets/master_presets_registry.json")

def create():
    presets = {
        "blueprint": {
            "preset_name": "blueprint",
            "display_name": "Blueprint",
            "description": "Blueprint motion graphics style pack.",
            "voice_name": "en_us_male_dry_narrator",
            "content_automation": {
                "title_structure": "Intriguing and high-impact title",
                "hook_style": "High curiosity and strong narrative tension",
                "target_words": 1800,
                "target_duration_minutes": 10,
                "tone": "Atmospheric, dramatic, engaging",
                "pacing": "Punchy, rhythmic, 160-180 wpm",
                "scene_density": "1 visual scene every 3-4 sentences"
            },
            "image_automation": {
                "visual_style": "engineering blueprint style, deep blue background with white ruled lines, technical lettering, no humans",
                "aspect_ratio": "16:9",
                "negative_prompt": "no photorealism, no 3D rendering, no soft lighting, no natural environments",
                "model": "Imagen 3",
                "generation_mode": "image",
                "character_consistency": "Preserve any defined character styling strictly in blueprint aesthetics",
                "environment_consistency": "Strict white lines on rich blueprint blue background (RGB: 27, 70, 155)",
                "cinematic_style": "Technical drawing, flat 2D layout"
            },
            "video_forge": {
                "allowed_transitions": ["cut", "fade", "dissolve"],
                "video_styling": "Blueprint rhythmic motion graphics",
                "sub_mode": "phrase",
                "sub_position": "bottom_center",
                "subtitle_font": "Arial-Bold",
                "subtitle_primary_color": "&H009B461B",
                "subtitle_outline_color": "&H00000000"
            }
        },
        "money_chuck": {
            "preset_name": "money_chuck",
            "display_name": "Money Chuck",
            "description": "White-background stick-figure doodle explainers about worst business decisions.",
            "voice_name": "en_us_male_dry_narrator",
            "content_automation": {
                "title_structure": "Top 10 Times ONE [singular trigger] [DESTROYED/KILLED/SAVED] a [beloved entity]",
                "hook_style": "Singular-agent schadenfreude: ONE decision, ONE ad, ONE mistake, ONE CEO.",
                "target_words": 2200,
                "target_duration_minutes": 10,
                "tone": "Deadpan, wry, third-person storyteller. Dry humor, never slapstick.",
                "pacing": "Short punchy sentences. ~170-190 words per minute.",
                "scene_density": "1 visual prompt per 2-3 narration sentences."
            },
            "image_automation": {
                "visual_style": "Minimalist black stick-figure doodle animation on a PURE WHITE background (#FFFFFF).",
                "aspect_ratio": "16:9",
                "negative_prompt": "photorealistic, 3d, shading, color gradients, textures",
                "model": "Imagen 3",
                "generation_mode": "image",
                "character_consistency": "Locked stick-figure design: circle head, thick rounded limbs.",
                "environment_consistency": "Background is ALWAYS pure white (#FFFFFF).",
                "cinematic_style": "Flat 2D doodle style with text cards and simple caricatures."
            },
            "video_forge": {
                "allowed_transitions": ["cut", "quick_zoom"],
                "video_styling": "fast-paced cuts, pop-up text annotations",
                "sub_mode": "phrase",
                "sub_position": "bottom_center",
                "subtitle_font": "Arial-Bold",
                "subtitle_primary_color": "&H00000000",
                "subtitle_outline_color": "&H00FFFFFF"
            }
        }
    }
    
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if REGISTRY_PATH.exists():
        try:
            existing = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        except Exception:
            existing = {}
    existing.update(presets)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    print(f"Master registry written to {REGISTRY_PATH}")

if __name__ == "__main__":
    create()
