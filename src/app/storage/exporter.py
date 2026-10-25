import os
import json
import re
from typing import Optional, List, Dict
from pathlib import Path

from app.models.generation import GenerationPackage
from app.models.preset import ContentPreset
from app.storage.sanitizer import sanitize_filename, sanitize_path
from app.prompts.parser import extract_script_text

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
        Strips potential leading/trailing whitespace or accidental system headers/JSON metadata.
        """
        if not script:
            return ""
        cleaned = extract_script_text(script, fallback="")
        if not cleaned or cleaned.strip().startswith("{"):
            # Never return raw JSON metadata strings as a script
            if not script.strip().startswith("{"):
                return script.strip()
            return ""
        return cleaned.strip()


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

    @classmethod
    def _get_or_generate_thumbnail_prompts(cls, package: GenerationPackage, preset: Optional[ContentPreset] = None) -> List[Dict[str, str]]:
        anchor = ""
        if package.continuity and package.continuity.art_style_anchor:
            anchor = package.continuity.art_style_anchor
        elif preset and hasattr(preset, "image_rules") and hasattr(preset.image_rules, "visual_style"):
            anchor = preset.image_rules.visual_style

        # Get preset thumbnail styles (default to 3 styles)
        styles = []
        resolved_preset = preset
        if resolved_preset is None and getattr(package, "preset_name", None):
            from app.models.preset import BUILTIN_PRESETS
            resolved_preset = BUILTIN_PRESETS.get(package.preset_name)

        if resolved_preset and hasattr(resolved_preset, "thumbnail_styles") and resolved_preset.thumbnail_styles:
            styles = resolved_preset.thumbnail_styles
        else:
            from app.models.preset import ContentPreset
            dummy = ContentPreset()
            styles = dummy.thumbnail_styles

        results = []
        existing_prompts = getattr(package, "thumbnail_prompts", []) or []

        for idx, s in enumerate(styles[:3]):
            s_id = getattr(s, "id", f"style_{idx+1}")
            s_name = getattr(s, "name", f"Style {idx+1}")
            s_desc = getattr(s, "description", "")

            if idx < len(existing_prompts) and existing_prompts[idx].strip():
                prompt_text = existing_prompts[idx].strip()
            else:
                p_name = resolved_preset.name if resolved_preset else "cinematic"
                prompt_text = (
                    f"A high-CTR YouTube thumbnail in the {p_name} style ({s_name}): {s_desc} "
                    f"Central narrative hook: High-tension dramatic visual staging for '{package.title}' ({package.topic}). "
                    f"Composition: 3-Element rule with ONE primary dominant focal subject occupying 45-50% of the canvas, "
                    f"stark figure-ground silhouette isolation, extreme mobile 300ms readability, high dynamic range chiaroscuro contrast. "
                    f"No text, no typography, no logos in the image. {anchor}"
                ).strip()

            results.append({
                "style_id": s_id,
                "style_name": s_name,
                "prompt": prompt_text
            })

        return results

    @classmethod
    def _format_thumbnail_prompt(cls, package: GenerationPackage, preset: Optional[ContentPreset] = None) -> str:
        """
        Formats 3 distinct built-in thumbnail prompts based on the preset styles, title, and topic.
        """
        prompts_data = cls._get_or_generate_thumbnail_prompts(package, preset)
        anchor = package.continuity.art_style_anchor if package.continuity and package.continuity.art_style_anchor else (preset.image_rules.visual_style if preset and hasattr(preset, 'image_rules') else '')

        lines = []
        lines.append(f"Title: {package.title}")
        lines.append(f"Topic: {package.topic}")
        if anchor:
            lines.append(f"Art Style Anchor: {anchor}")
        lines.append("")

        for i, item in enumerate(prompts_data, 1):
            lines.append(f"--- Thumbnail Style {i}: {item['style_name']} ---")
            lines.append(f"Thumbnail Prompt: {item['prompt']}\n")

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

        # 3.6 Extract chapters from script and write initial chapters.txt
        from app.prompts.parser import extract_chapters_from_script
        chapters_data = extract_chapters_from_script(script_content)
        if chapters_data:
            initial_chapter_lines = []
            for idx, ch in enumerate(chapters_data):
                ts = "00:00" if idx == 0 else "--:--"
                initial_chapter_lines.append(f"{ts} - {ch['title']}")
            (target_dir / "chapters.txt").write_text("\n".join(initial_chapter_lines), encoding="utf-8")

        # 4. Write project.json (formerly metadata.json)
        if include_metadata:
            target_voice_id = getattr(package, 'voice_name', None)
            if not target_voice_id and preset and hasattr(preset, 'voice_name'):
                target_voice_id = preset.voice_name
            if not target_voice_id or "Adam" in str(target_voice_id):
                target_voice_id = "Adam   ·  American Male"

            target_language = getattr(package, 'video_language', None)
            if not target_language and preset and hasattr(preset, 'video_language'):
                target_language = preset.video_language
            if not target_language:
                target_language = "English"

            cleaned_seo_desc = package.seo_description or ""
            for artifact_kw in ["empty_response", "skill_result", "memory_search", "successtrue", "totaltokens", "[skill result"]:
                if artifact_kw in cleaned_seo_desc.lower():
                    cleaned_seo_desc = f"An in-depth video story and explanation covering {package.topic}."
                    break

            thumb_data = cls._get_or_generate_thumbnail_prompts(package, preset)
            package.thumbnail_prompts = [item["prompt"] for item in thumb_data]

            meta_dict = {
                "stage": "SCRIPT_READY",
                "status": "PENDING",
                "topic": package.topic,
                "preset_name": preset.name if preset and preset.name else package.preset_name,
                "voice_name": target_voice_id,
                "voice_id": target_voice_id,
                "voice": target_voice_id,
                "video_language": target_language,
                "title": package.title,
                "seo_tags": getattr(package, 'seo_tags', []),
                "seo_description": cleaned_seo_desc,
                "normalized_title": package.normalized_title,
                "thumbnail_prompts": thumb_data,
                "thumbnail_prompt": thumb_data[0]["prompt"] if thumb_data else "",
                "chapters": [{"title": ch["title"], "first_sentence": ch["first_sentence"]} for ch in chapters_data] if chapters_data else [],
                "total_words": package.total_words,
                "estimated_duration_sec": float(package.estimated_duration_sec) if package.estimated_duration_sec else 0.0,
                "quality_score": float(package.quality_score) if package.quality_score else 0.0,
                "reviewer_notes": package.reviewer_notes,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
                        # Append timestamps if chapters are available
            chapters_file = target_dir / "chapters.txt"
            if chapters_file.exists():
                ch_text = chapters_file.read_text(encoding="utf-8").strip()
                if ch_text and "00:00" in ch_text and "--:--" not in ch_text and "00:00" not in meta_dict.get("seo_description", ""):
                    meta_dict["seo_description"] = meta_dict["seo_description"].rstrip() + "\n\nTimestamps:\n" + ch_text

            (target_dir / "project.json").write_text(json.dumps(meta_dict, indent=2, ensure_ascii=False), encoding="utf-8")

        return str(target_dir)

    @classmethod
    def write_prompts_to_existing_project(cls, project_dir: Path, package: GenerationPackage, preset: Optional[ContentPreset] = None) -> bool:
        """
        Appends or updates prompts.txt and project.json in an existing project folder
        after audio has been transcribed.
        """
        if not project_dir.exists() or not package.prompts:
            return False

        # Support both metadata.json (legacy) and project.json (new format)
        meta_path = project_dir / "project.json"
        if not meta_path.exists():
            meta_path = project_dir / "metadata.json"

        resolved_preset = preset
        preset_name_from_meta = ""
        if meta_path.exists():
            try:
                _meta_peek = json.loads(meta_path.read_text(encoding="utf-8"))
                preset_name_from_meta = _meta_peek.get("preset_name", "")
            except Exception:
                pass

        if resolved_preset is None:
            pname = getattr(package, "preset_name", None) or preset_name_from_meta
            if pname:
                from app.models.preset import BUILTIN_PRESETS
                resolved_preset = BUILTIN_PRESETS.get(pname)

        prompts_content = cls._format_prompts(package)
        (project_dir / "prompts.txt").write_text(prompts_content, encoding="utf-8")

        # Ensure thumbnail_prompt.txt exists
        thumb_file = project_dir / "thumbnail_prompt.txt"
        if not thumb_file.exists():
            thumb_content = cls._format_thumbnail_prompt(package, preset=resolved_preset)
            thumb_file.write_text(thumb_content, encoding="utf-8")

        if meta_path.exists():
            try:
                meta_dict = json.loads(meta_path.read_text(encoding="utf-8"))
                meta_dict["stage"] = "PROMPTS_READY"
                meta_dict["prompts_generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if "thumbnail_prompts" not in meta_dict:
                    thumb_data = cls._get_or_generate_thumbnail_prompts(package, preset=resolved_preset)
                    meta_dict["thumbnail_prompts"] = thumb_data
                    meta_dict["thumbnail_prompt"] = thumb_data[0]["prompt"] if thumb_data else ""
                # Check if chapters.txt has timestamps to append to seo_description
                chapters_file = project_dir / "chapters.txt"
                if chapters_file.exists():
                    ch_text = chapters_file.read_text(encoding="utf-8").strip()
                    cur_desc = meta_dict.get("seo_description", "")
                    if ch_text and "00:00" in ch_text and "--:--" not in ch_text and "00:00" not in cur_desc:
                        meta_dict["seo_description"] = cur_desc.rstrip() + "\n\nTimestamps:\n" + ch_text

                if "Adam" in str(meta_dict.get("voice_name", "")):
                    meta_dict["voice_name"] = "Adam   ·  American Male"
                    meta_dict["voice_id"] = "Adam   ·  American Male"
                    meta_dict["voice"] = "Adam   ·  American Male"

                # When updating, if it was legacy metadata.json, save as project.json instead
                new_meta_path = project_dir / "project.json"
                new_meta_path.write_text(json.dumps(meta_dict, indent=2, ensure_ascii=False), encoding="utf-8")
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

