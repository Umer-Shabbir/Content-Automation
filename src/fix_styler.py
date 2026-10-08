from pathlib import Path
import re

p = Path("H:/Automation/Video Forge/app/subtitles/styler.py")
content = p.read_text(encoding="utf-8")

if "from app.core.project import RenderProfile" not in content:
    content = "from app.core.project import RenderProfile\n" + content
    p.write_text(content, encoding="utf-8")
    print("Styler patched")
