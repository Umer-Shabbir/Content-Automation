import re

with open(r'H:\Automation\Video Forge\app\utils\file_utils.py', 'r', encoding='utf-8') as f:
    text = f.read()

pattern = r'    full_text_clean = " ".join\(s\["text"\] for s in segments\)\n    return full_text_clean, segments\n    """\n    Return a list of folders'
replacement = '    full_text_clean = " ".join(s["text"] for s in segments)\n    return full_text_clean, segments\n\ndef scan_for_project_folders(root: Path, recursive: bool = True, max_depth: int = 4) -> list[Path]:\n    """\n    Return a list of folders'

text = re.sub(pattern, replacement, text)

with open(r'H:\Automation\Video Forge\app\utils\file_utils.py', 'w', encoding='utf-8') as f:
    f.write(text)
