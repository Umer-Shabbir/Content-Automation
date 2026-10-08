from pathlib import Path

p = Path("H:/Automation/Image Automation/worker.py")
content = p.read_text(encoding="utf-8")

replacement = """        # Load preset if specified
        preset_name = self._s("style_preset", "")
        preset_visual_style = ""
        preset_aspect_ratio = ""

        if job.project_folder:
            import json
            pjson_path = Path(job.project_folder) / "project.json"
            if not pjson_path.exists():
                pjson_path = Path(job.project_folder) / "metadata.json"
            
            if pjson_path.exists():
                try:
                    pdata = json.loads(pjson_path.read_text(encoding="utf-8"))
                    preset_name = pdata.get("preset_name", preset_name)
                except Exception:
                    pass
                    
        if preset_name:
            try:
                import json
                registry_path = Path("H:/Automation/Presets/master_presets_registry.json")
                if registry_path.exists():
                    registry = json.loads(registry_path.read_text(encoding="utf-8"))
                    if preset_name in registry:
                        ia = registry[preset_name].get("image_automation", {})
                        preset_visual_style = ia.get("visual_style", "")
                        preset_aspect_ratio = ia.get("aspect_ratio", "")
            except Exception as e:
                self._log(f"Failed to load preset {preset_name}: {e}", "warning")

        # 2. Build final prompt with @Character tag
        final_prompt = build_final_prompt(
            base           = job.prompt_text,
            character_name = char_name,
            prefix         = self._s("prompt_prefix", ""),
            suffix         = self._s("prompt_suffix", ""),
            style          = preset_visual_style or self._s("style_preset", ""),
            aspect_ratio   = preset_aspect_ratio or job.aspect_ratio or self._s("aspect_ratio", "16:9"),
        )"""

# Instead of regex, let's use a simpler target replacement.
# Let's see what's currently in worker.py
target = """        # Load preset if specified
        preset_name = self._s("style_preset", "")
        preset_visual_style = ""
        preset_aspect_ratio = ""
        if preset_name:
            try:
                import json
                registry_path = Path("H:/Automation/Presets/master_presets_registry.json")
                if registry_path.exists():
                    registry = json.loads(registry_path.read_text(encoding="utf-8"))
                    if preset_name in registry:
                        ia = registry[preset_name].get("image_automation", {})
                        preset_visual_style = ia.get("visual_style", "")
                        preset_aspect_ratio = ia.get("aspect_ratio", "")
            except Exception as e:
                self._log(f"Failed to load preset {preset_name}: {e}", "warning")

        # 2. Build final prompt with @Character tag
        final_prompt = build_final_prompt(
            base           = job.prompt_text,
            character_name = char_name,
            prefix         = self._s("prompt_prefix", ""),
            suffix         = self._s("prompt_suffix", ""),
            style          = preset_visual_style or self._s("style_preset", ""),
            aspect_ratio   = preset_aspect_ratio or job.aspect_ratio or self._s("aspect_ratio", "16:9"),
        )"""

if target in content:
    content = content.replace(target, replacement)
    p.write_text(content, encoding="utf-8")
    print("worker.py patched successfully")
else:
    print("Could not find target in worker.py")
