import re

with open(r"H:\Automation\Image Automation\backend\app\routers\queue.py", "r", encoding="utf-8") as f:
    content = f.read()

# We need to parse thumbnail_prompt.txt if it exists
new_logic = """        # Parse thumbnail_prompt.txt if it exists
        thumbnail_file = folder / "thumbnail_prompt.txt"
        thumbnail_prompt = None
        if thumbnail_file.exists():
            thumbnail_prompt = thumbnail_file.read_text(encoding="utf-8").strip()

        # Parse prompts.txt to determine how many lines there are"""

content = content.replace("        # Parse prompts.txt to determine how many lines there are", new_logic)

new_logic2 = """
        for p_idx, p_text in enumerate(raw_prompts):
            j = Job(
                id=str(uuid.uuid4()),
                topic_name=topic_name,
                topic_slug=slugify(topic_name),
                topic_index=len(jobs) + 1,
                prompt_text=p_text,
                prompt_index=p_idx + 1,
                global_index=start_global_idx,
                prompt_slug=slugify(p_text[:40]),
                status=JobStatus.PENDING,
                character_name=char_name,
                model_name=model_name,
                mode=mode,
                aspect_ratio=ar,
                project_folder=str(folder)
            )
            jobs.append(j)
            start_global_idx += 1
            
        if thumbnail_prompt:
            # Add thumbnail job with prompt_index=-1 and prompt_slug='thumbnail'
            j = Job(
                id=str(uuid.uuid4()),
                topic_name=topic_name,
                topic_slug=slugify(topic_name),
                topic_index=len(jobs) + 1,
                prompt_text=thumbnail_prompt,
                prompt_index=-1,
                global_index=start_global_idx,
                prompt_slug="thumbnail",
                status=JobStatus.PENDING,
                character_name=char_name,
                model_name=model_name,
                mode=mode,
                aspect_ratio=ar,
                project_folder=str(folder)
            )
            jobs.append(j)
            start_global_idx += 1
"""
content = re.sub(r'        for p_idx, p_text in enumerate\(raw_prompts\):[\s\S]*?start_global_idx \+= 1', new_logic2.strip('\n'), content)

# Update validation logic for skip
new_validation = """        # Validation logic to skip if images directory is fully populated
        images_dir = folder / "images"
        images_complete = False
        if images_dir.exists() and images_dir.is_dir():
            image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
            existing_images = [f for f in images_dir.iterdir() if f.is_file() and f.suffix.lower() in image_extensions]
            if len(existing_images) >= len(raw_prompts):
                images_complete = True
                
        thumbnail_complete = True
        if thumbnail_prompt:
            thumbnail_complete = (folder / "thumbnail.jpg").exists() or (folder / "thumbnail.png").exists() or (folder / "thumbnail.jpeg").exists()
            
        if images_complete and thumbnail_complete:
            # Update project.json state just in case it wasn't done
            if project_json_file.exists():
                try:
                    meta["stage"] = "IMAGES_READY"
                    meta["status"] = "COMPLETED"
                    project_json_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                except Exception:
                    pass
            return False, f"{folder.name} (Already fully generated)" """

# Need to replace the exact validation logic
content = re.sub(r'        # Validation logic to skip if images directory is fully populated[\s\S]*?return False,.*?images\)"', new_validation.strip('\n'), content)

with open(r"H:\Automation\Image Automation\backend\app\routers\queue.py", "w", encoding="utf-8") as f:
    f.write(content)

