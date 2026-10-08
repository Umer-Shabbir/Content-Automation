from pathlib import Path

p = Path("H:/Automation/Video Forge/app/subtitles/styler.py")
content = p.read_text(encoding="utf-8")

content = "from typing import Optional\n" + content
p.write_text(content, encoding="utf-8")

