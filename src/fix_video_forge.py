import json
from pathlib import Path
import re

REGISTRY_PATH = Path('H:/Automation/Presets/master_presets_registry.json')
registry = json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))

p = Path("H:/Automation/Video Forge/app/storage/settings_manager.py")
content = p.read_text(encoding="utf-8")

replacement = """    @staticmethod
    def _default_presets() -> dict:
        \"\"\"Built-in presets shipped with the application, loaded from master registry.\"\"\"
        presets = {}
        
        # Load from master registry if it exists
        try:
            import json
            from pathlib import Path
            from app.core.project import RenderProfile, SubtitleMode, TransitionType, MotionType
            
            registry_path = Path("H:/Automation/Presets/master_presets_registry.json")
            if registry_path.exists():
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
                for preset_name, data in registry.items():
                    vf = data.get("video_forge", {})
                    p = RenderProfile()
                    # Apply defaults from our standard video forge config mapping
                    # Assuming 16:9 for most
                    ia = data.get("image_automation", {})
                    aspect = ia.get("aspect_ratio", "16:9")
                    if aspect == "9:16":
                        p.width, p.height = 1080, 1920
                    elif aspect == "1:1":
                        p.width, p.height = 1080, 1080
                    else:
                        p.width, p.height = 1920, 1080
                    
                    p.fps = 30
                    p.video_bitrate = "6M"
                    p.crf = 20
                    
                    sub_mode = vf.get("sub_mode", "phrase")
                    if sub_mode == "phrase": p.subtitle_mode = SubtitleMode.PHRASE
                    elif sub_mode == "classic": p.subtitle_mode = SubtitleMode.CLASSIC
                    elif sub_mode == "viral": p.subtitle_mode = SubtitleMode.VIRAL
                    elif sub_mode == "word": p.subtitle_mode = SubtitleMode.WORD
                    elif sub_mode == "karaoke": p.subtitle_mode = SubtitleMode.KARAOKE
                    
                    trans = vf.get("allowed_transitions", ["fade"])
                    if "cut" in trans and len(trans) == 1: p.transition_type = TransitionType.CUT
                    elif "dissolve" in trans: p.transition_type = TransitionType.DISSOLVE
                    elif "quick_zoom" in trans: p.transition_type = TransitionType.ZOOM_IN
                    elif "swipe" in trans: p.transition_type = TransitionType.SWIPE_LEFT
                    else: p.transition_type = TransitionType.FADE
                    
                    p.motion_type = MotionType.KEN_BURNS
                    
                    p.subtitle_font = vf.get("subtitle_font", "Arial-Bold")
                    p.subtitle_primary_color = vf.get("subtitle_primary_color", "&H00FFFFFF")
                    p.subtitle_outline_color = vf.get("subtitle_outline_color", "&H00000000")
                    
                    presets[preset_name] = p.to_dict()
        except Exception as e:
            import logging
            log = logging.getLogger("videoforge.settings")
            log.warning(f"Could not load master registry presets: {e}")

        # YouTube / 16:9 HD fallback
        p = RenderProfile()
        p.width, p.height = 1920, 1080
        p.fps = 30
        p.video_bitrate = "6M"
        p.crf = 20
        p.subtitle_mode = SubtitleMode.CLASSIC
        p.subtitle_font_size = 64
        # We need to not overwrite if they exist, but actually it's fine just to keep our defaults too
        presets["YouTube HD (16:9)"] = p.to_dict()

        # Reels / Shorts 9:16
        p2 = RenderProfile()
        p2.width, p2.height = 1080, 1920
        p2.fps = 30
        p2.video_bitrate = "4M"
        p2.subtitle_mode = SubtitleMode.VIRAL
        p2.subtitle_font_size = 80
        p2.subtitle_margin_v = 200
        p2.transition_type = TransitionType.FADE
        p2.motion_type = MotionType.KEN_BURNS
        presets["Reels / Shorts (9:16)"] = p2.to_dict()

        return presets"""

# Let's replace the whole `_default_presets` staticmethod
lines = content.splitlines()
start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if "def _default_presets() -> dict:" in line:
        start_idx = i - 1 # include @staticmethod
    elif start_idx != -1 and i > start_idx + 2 and "def get_app_data_dir() -> Path:" in line:
        end_idx = i - 2
        break

if start_idx != -1 and end_idx != -1:
    new_content = "\n".join(lines[:start_idx]) + "\n" + replacement + "\n\n" + "\n".join(lines[end_idx+1:])
    p.write_text(new_content, encoding="utf-8")
    print("Video Forge settings_manager.py patched successfully")
else:
    print("Could not find _default_presets block")
