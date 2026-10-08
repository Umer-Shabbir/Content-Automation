from pathlib import Path
import re

p = Path("H:/Automation/Image Automation/models.py")
content = p.read_text(encoding="utf-8")

# Let's replace the properties if needed, but since it already had it, we just want to expose the master presets loader

