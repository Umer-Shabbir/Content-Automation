from pathlib import Path

p = Path("H:/Automation/Video Forge/app/subtitles/styler.py")
content = p.read_text(encoding="utf-8")

if "from app.core.project import" not in content[:300]:
    content = "from app.core.project import RenderProfile, SubtitleMode\n" + content
    p.write_text(content, encoding="utf-8")

