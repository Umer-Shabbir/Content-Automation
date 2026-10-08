from pathlib import Path

p = Path("H:/Automation/Video Forge/app/subtitles/styler.py")
content = p.read_text(encoding="utf-8")

if "from typing import" not in content:
    content = "from typing import Optional, List\n" + content
elif "Optional" not in content:
    content = content.replace("from typing import ", "from typing import Optional, ")
p.write_text(content, encoding="utf-8")
