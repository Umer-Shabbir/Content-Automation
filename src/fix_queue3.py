import os
from pathlib import Path
_AUTOMATION_ROOT = Path(os.getenv('AUTOMATION_ROOT', Path(__file__).resolve().parents[2]))
_PRESETS_PATH = Path(os.getenv('MASTER_PRESETS_PATH', _AUTOMATION_ROOT / 'presets' / 'master_presets_registry.json'))
import re
with open(_AUTOMATION_ROOT / 'Image Automation' / 'backend' / 'app' / 'routers' / 'queue.py', "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Read thumbnail_prompt before the raw_prompts empty check.
pattern = r"""        if not raw_prompts:
            return False, f"{folder.name} \(No valid prompts parsed from prompts\.txt\)"


        # Check for thumbnail prompt
        thumbnail_prompt_file = folder / "thumbnail_prompt.txt"
        thumbnail_prompt_text = ""
        if thumbnail_prompt_file.exists\(\):
            thumbnail_prompt_text = thumbnail_prompt_file.read_text\(encoding="utf-8"\).strip\(\)"""

replacement = """        # Check for thumbnail prompt
        thumbnail_prompt_file = folder / "thumbnail_prompt.txt"
        thumbnail_prompt_text = ""
        if thumbnail_prompt_file.exists():
            thumbnail_prompt_text = thumbnail_prompt_file.read_text(encoding="utf-8").strip()

        if not raw_prompts and not thumbnail_prompt_text:
            return False, f"{folder.name} (No valid prompts parsed from prompts.txt and no thumbnail)"
"""
content = re.sub(pattern, replacement, content, count=1)

with open(_AUTOMATION_ROOT / 'Image Automation' / 'backend' / 'app' / 'routers' / 'queue.py', "w", encoding="utf-8") as f:
    f.write(content)
