from pathlib import Path
import re

p = Path("H:/Automation/Video Forge/app/subtitles/styler.py")
content = p.read_text(encoding="utf-8")

if "from app.core.project import " not in content:
    # Need to add import
    pass 
else:
    # Let's just fix it
    if "RenderProfile" not in content and "def _get_speaker_color(" in content:
        # We need to add RenderProfile to the imports
        content = re.sub(r"(from app\.core\.project import[^\n]*)(FitMode|SubtitleMode|TransitionType)", r"\1RenderProfile, \2", content)
        p.write_text(content, encoding="utf-8")

