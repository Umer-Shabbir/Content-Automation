from pathlib import Path

p = Path("H:/Automation/Image Automation/queue_manager.py")
content = p.read_text(encoding="utf-8")

for i, line in enumerate(content.splitlines()):
    if "project.json" in line or "metadata.json" in line:
        print(f"{i}: {line}")

