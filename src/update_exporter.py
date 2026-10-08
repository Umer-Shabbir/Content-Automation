import re

with open(r"H:\Automation\Content Automation\src\app\storage\exporter.py", "r") as f:
    content = f.read()

# Add _format_thumbnail_prompt method right after _format_prompts
thumbnail_method = """    @staticmethod
    def _format_thumbnail_prompt(package: GenerationPackage, preset: Optional[ContentPreset] = None) -> str:
        \"\"\"
        Formats a dedicated thumbnail prompt based on the title, topic, and art style.
        \"\"\"
        lines = []
        lines.append(f"Title: {package.title}")
        lines.append(f"Topic: {package.topic}")
        if package.continuity and package.continuity.art_style_anchor:
            lines.append(f"Art Style Anchor: {package.continuity.art_style_anchor}")
        
        # Build the actual prompt
        prompt = f"A compelling, high-contrast YouTube thumbnail for a video titled '{package.title}'. "
        if package.continuity and package.continuity.art_style_anchor:
            prompt += f"Style: {package.continuity.art_style_anchor}. "
        
        prompt += "The image should have clear focal points, vibrant colors, and be visually striking. No text in the image."
        
        lines.append(f"\nThumbnail Prompt: {prompt}\n")
        return "\n".join(lines).strip()

"""
# Find where _get_unique_dir starts to insert before it
idx = content.find("    @staticmethod\n    def _get_unique_dir")
if idx > -1:
    content = content[:idx] + thumbnail_method + content[idx:]

# Find where to save thumbnail_prompt.txt
save_idx = content.find("        # 4. Write project.json")
if save_idx > -1:
    save_code = """        # 3.5 Write thumbnail_prompt.txt
        thumbnail_content = cls._format_thumbnail_prompt(package, preset)
        (target_dir / "thumbnail_prompt.txt").write_text(thumbnail_content, encoding="utf-8")

"""
    content = content[:save_idx] + save_code + content[save_idx:]

with open(r"H:\Automation\Content Automation\src\app\storage\exporter.py", "w") as f:
    f.write(content)
print("Updated exporter.py")
