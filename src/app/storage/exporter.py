import os
import json
import re
from typing import Optional
from pathlib import Path

from app.models.generation import GenerationPackage
from app.models.preset import ContentPreset
from app.storage.sanitizer import sanitize_filename, sanitize_path

from datetime import datetime, timezone

class ContentExporter:
    """
    Exports a completed GenerationPackage into a clean folder structure.
    Atomically writes the required output files and prevents folder collisions.
    """

    def __init__(self, base_output_dir: Optional[str] = "output"):
        self.base_output_dir = base_output_dir

    @staticmethod
    def _validate_script_text(script: str) -> str:
        """
        Ensures the script is clean voice-over narration only.
        Strips potential leading/trailing whitespace or accidental system headers.
        """
        cleaned = script.strip()
        return cleaned

    @staticmethod
    def _format_prompts(package: GenerationPackage) -> str:
        """
        Formats scene prompts into a structured readable text block.
        """
        if not package.prompts:
            return ""

        lines = []
        if package.continuity and package.continuity.art_style_anchor:
            lines.append(f"Art Style Anchor: {package.continuity.art_style_anchor}\n")

        for prompt in package.prompts:
            lines.append(f"--- SCENE {prompt.scene_number} ---")

            # Print timestamp range if available (e.g. 00:00:05,000 --> 00:00:10,500)
            if prompt.start_time or prompt.end_time:
                time_range = f"{prompt.start_time or '00:00:00,000'} --> {prompt.end_time or '00:00:00,000'}"
                lines.append(f"[{time_range}]")

            if prompt.narration_segment:
                lines.append(f"Narration: {prompt.narration_segment}")
            if prompt.visual_description:
                lines.append(f"Visual: {prompt.visual_description}")
            if prompt.characters_present:
                lines.append(f"Characters: {', '.join(prompt.characters_present)}")
            if prompt.location:
                lines.append(f"Location: {prompt.location}")
            if prompt.mood_lighting:
                lines.append(f"Lighting/Mood: {prompt.mood_lighting}")
            if prompt.camera_angle:
                lines.append(f"Camera: {prompt.camera_angle}")
            lines.append(f"Image Prompt: {prompt.detailed_image_prompt}\n")

        return "\n".join(lines).strip()

    @staticmethod
    def _format_thumbnail_prompt(package: GenerationPackage, preset: Optional[ContentPreset] = None) -> str:
        """
        Formats a dedicated thumbnail prompt based on the title, topic, and art style.
        """
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

    @staticmethod
    def _get_unique_dir(base_path: Path, folder_name: str) -> Path:
        """
        Resolves folder name collisions by appending (1), (2), etc.
        """
        target_dir = base_path / folder_name
        if not target_dir.exists():
            return target_dir

        counter = 1
        while True:
            candidate = base_path / f"{folder_name} ({counter})"
            if not candidate.exists():
                return candidate
            counter += 1

    @classmethod
    def export_package(
        cls,
        package: GenerationPackage,
        base_output_dir: Optional[str] = None,
        preset: Optional[ContentPreset] = None,
        include_metadata: bool = True
    ) -> str:
        """
        Exports a GenerationPackage to disk.
        """
        raw_base_dir = base_output_dir
        if not raw_base_dir and preset:
            raw_base_dir = preset.output_dir
        if not raw_base_dir:
            raw_base_dir = "output"

        safe_base_str = sanitize_path(raw_base_dir)
        base_path = Path(safe_base_str).resolve()
        base_path.mkdir(parents=True, exist_ok=True)

        folder_title = package.normalized_title or package.title or "untitled_project"
        safe_folder_name = sanitize_filename(folder_title)

        target_dir = cls._get_unique_dir(base_path, safe_folder_name)
        target_dir.mkdir(parents=True, exist_ok=False)

        # 1. Write title.txt (strictly the title text only)
        title_content = package.title.strip()
        (target_dir / "title.txt").write_text(title_content, encoding="utf-8")

        # 2. Write script.txt (strictly voice-over narration)
        script_content = cls._validate_script_text(package.script)
        (target_dir / "script.txt").write_text(script_content, encoding="utf-8")

        # 3. Write prompts.txt ONLY if prompts exist
        if package.prompts:
            prompts_content = cls._format_prompts(package)
            (target_dir / "prompts.txt").write_text(prompts_content, encoding="utf-8")

        # 3.5 Write thumbnail_prompt.txt
        thumbnail_content = cls._format_thumbnail_prompt(package, preset)
        (target_dir / "thumbnail_prompt.txt").write_text(thumbnail_content, encoding="utf-8")

        # 4. Write project.json (formerly metadata.json)
        if include_metadata:
            meta_dict = {
                "stage": "SCRIPT_READY",
                "status": "PENDING",
                "topic": package.topic,
                "preset_name": preset.name if preset and preset.name else package.preset_name,
                "voice_name": preset.voice_name if preset and hasattr(preset, 'voice_name') and preset.voice_name else getattr(package, 'voice_name', 'en_us_male_dry_narrator'),
                "title": package.title,
                "normalized_title": package.normalized_title,
                "total_words": package.total_words,
                "estimated_duration_sec": float(package.estimated_duration_sec) if package.estimated_duration_sec else 0.0,
                "quality_score": float(package.quality_score) if package.quality_score else 0.0,
                "reviewer_notes": package.reviewer_notes,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            (target_dir / "project.json").write_text(json.dumps(meta_dict, indent=2), encoding="utf-8")

        return str(target_dir)

    @classmethod
    def write_prompts_to_existing_project(cls, project_dir: Path, package: GenerationPackage) -> bool:
        """
        Appends or updates prompts.txt and project.json in an existing project folder
        after audio has been transcribed.
        """
        if not project_dir.exists() or not package.prompts:
            return False

        prompts_content = cls._format_prompts(package)
        (project_dir / "prompts.txt").write_text(prompts_content, encoding="utf-8")

        # Support both metadata.json (legacy) and project.json (new format)
        meta_path = project_dir / "project.json"
        if not meta_path.exists():
            meta_path = project_dir / "metadata.json"

        if meta_path.exists():
            try:
                meta_dict = json.loads(meta_path.read_text(encoding="utf-8"))
                meta_dict["stage"] = "PROMPTS_READY"
                meta_dict["prompts_generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                # When updating, if it was legacy metadata.json, save as project.json instead
                new_meta_path = project_dir / "project.json"
                new_meta_path.write_text(json.dumps(meta_dict, indent=2), encoding="utf-8")
                # Optionally remove the old metadata.json if it exists and we're converting
                if meta_path.name == "metadata.json" and new_meta_path.exists():
                    try:
                        meta_path.unlink()
                    except OSError:
                        pass
            except Exception:
                pass
        return True

    def export(self, package: GenerationPackage, include_metadata: bool = True) -> str:
        """Instance method adapter for export_package."""
        return self.export_package(package, base_output_dir=self.base_output_dir, include_metadata=include_metadata)

