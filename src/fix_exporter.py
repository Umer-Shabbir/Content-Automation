import re

with open("app/storage/exporter.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the broken f-string literals that cause syntax errors
content = content.replace('lines.append(f"\nThumbnail Prompt: {prompt}\n")', 'lines.append(f"\nThumbnail Prompt: {prompt}\n")')
content = content.replace('return "\n".join(lines).strip()', 'return "\n".join(lines).strip()')

with open("app/storage/exporter.py", "w", encoding="utf-8") as f:
    f.write(content)

