from pathlib import Path
import re

p = Path("H:/Automation/Content Automation/src/app/models/preset.py")
content = p.read_text(encoding="utf-8")

replacement = """def load_builtin_presets() -> dict:
    registry_path = Path("H:/Automation/Presets/master_presets_registry.json")
    presets = {}
    if registry_path.exists():
        try:
            import json
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            for slug, item in data.items():
                ca = item.get("content_automation", {})
                ia = item.get("image_automation", {})
                
                # Check for list structures in forbidden patterns
                forbidden = ca.get("forbidden_patterns", ["You won't believe", "Shocking truth", "Gone wrong"])
                if isinstance(forbidden, str):
                    forbidden = [f.strip() for f in forbidden.split(",")]
                    
                presets[slug] = ContentPreset(
                    name=slug,
                    description=item.get("description", ""),
                    voice_name=item.get("voice_name", "en_us_male_dry_narrator"),
                    is_builtin=True,
                    title_rules=TitleRules(
                        title_structure=ca.get("title_structure", "Clear and intriguing title"),
                        hook_style=ca.get("hook_style", "High curiosity and tension"),
                        forbidden_patterns=forbidden,
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
                        cinematic_style=ia.get("cinematic_style", "Cinematic layout"),
                        aspect_ratio=ia.get("aspect_ratio", "16:9"),
                        scene_density=ca.get("scene_density", "1 visual scene every 3-4 sentences"),
                        character_consistency=ia.get("character_consistency", ""),
                        environment_consistency=ia.get("environment_consistency", "")
                    ),
                    reviewer_rules=ReviewerRules(min_quality_score=8.5, max_revisions=3)
                )
        except Exception as e:
            print(f"Error loading presets: {e}")
    if "money_chuck" not in presets:
        presets["money_chuck"] = ContentPreset()
    return presets"""

# Regex replacing the old function
content = re.sub(r"def load_builtin_presets\(\) -> dict:.*?return presets", replacement, content, flags=re.DOTALL)
p.write_text(content, encoding="utf-8")
print("Content preset patched")
