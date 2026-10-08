from pathlib import Path
import re

p = Path("H:/Automation/Video Forge/app/storage/settings_manager.py")
content = p.read_text(encoding="utf-8")

replacement = """def _default_presets() -> dict:
        \"""Built-in presets, loaded dynamically from registry and merged with hardcoded fallback defaults.\"""
        presets = {}

        # Default fallback FFmpeg presets
        from app.core.project import RenderProfile, SubtitleMode, TransitionType, MotionType
        
        # Fast preview
        p4 = RenderProfile()
        p4.width, p4.height = 1280, 720
        p4.fps = 24
        p4.video_bitrate = "2M"
        p4.crf = 28
        p4.preset_name = "ultrafast"  # ffmpeg preset
        p4.motion_type = MotionType.NONE
        p4.subtitle_mode = SubtitleMode.CLASSIC
        presets["Fast Preview (720p)"] = p4.to_dict()

        # High quality
        p5 = RenderProfile()
        p5.width, p5.height = 1920, 1080
        p5.fps = 30
        p5.video_bitrate = "10M"
        p5.crf = 16
        p5.preset_name = "slow"  # ffmpeg preset
        p5.motion_type = MotionType.KEN_BURNS
        p5.motion_intensity = 1.5
        presets["High Quality Archive"] = p5.to_dict()

        # Try load master registry
        try:
            import json
            registry_path = Path("H:/Automation/Presets/master_presets_registry.json")
            if registry_path.exists():
                data = json.loads(registry_path.read_text(encoding="utf-8"))
                for slug, item in data.items():
                    vf = item.get("video_forge", {})
                    p = RenderProfile()
                    
                    # Basic 16:9 Defaults
                    p.width, p.height = 1920, 1080
                    p.fps = 30
                    p.video_bitrate = "6M"
                    p.crf = 20
                    
                    # Mappings from master registry
                    transitions_list = vf.get("allowed_transitions", [])
                    p.transition_type = TransitionType.FADE # default
                    if "cut" in transitions_list and len(transitions_list) == 1:
                        p.transition_type = TransitionType.CUT
                    elif "dissolve" in transitions_list:
                        p.transition_type = TransitionType.DISSOLVE

                    sub_mode = vf.get("sub_mode", "phrase")
                    if sub_mode == "phrase":
                        p.subtitle_mode = SubtitleMode.PHRASE
                    elif sub_mode == "viral":
                        p.subtitle_mode = SubtitleMode.VIRAL
                    elif sub_mode == "karaoke":
                        p.subtitle_mode = SubtitleMode.KARAOKE
                    else:
                        p.subtitle_mode = SubtitleMode.CLASSIC
                        
                    p.subtitle_font = vf.get("subtitle_font", "Arial-Bold")
                    p.subtitle_primary_color = vf.get("subtitle_primary_color", "&H00FFFFFF")
                    p.subtitle_outline_color = vf.get("subtitle_outline_color", "&H00000000")
                    
                    if vf.get("sub_position") == "bottom_center":
                        p.subtitle_margin_v = 80
                    elif vf.get("sub_position") == "center":
                        p.subtitle_margin_v = 500
                        
                    presets[slug] = p.to_dict()
        except Exception as e:
            log.error(f"Failed to load master registry presets: {e}")

        return presets"""

content = re.sub(r"def _default_presets.*?return presets", replacement, content, flags=re.DOTALL)
p.write_text(content, encoding="utf-8")
print("Video forge presets patched.")
