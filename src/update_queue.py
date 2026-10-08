import re

file_path = r"H:\Automation\Image Automation\backend\app\routers\queue.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# I will use regular expressions to find the place and inject the thumbnail job logic

import_project_pattern = r"""(        # Validation logic to skip if images directory is fully populated\s*images_dir = folder / "images".*?)(        model_name = data.override_model or settings.default_model or "Nano Banana")"""

def replacement(m):
    original = m.group(1)
    model_name = m.group(2)
    
    # We will modify the return False to instead just not queue the regular prompts, 
    # but still allow thumbnail to be queued.
    new_logic = """        # Check for thumbnail prompt
        thumbnail_prompt_file = folder / "thumbnail_prompt.txt"
        thumbnail_prompt_text = ""
        if thumbnail_prompt_file.exists():
            thumbnail_prompt_text = thumbnail_prompt_file.read_text(encoding="utf-8").strip()

        # Validation logic to skip if images directory is fully populated
        images_dir = folder / "images"
        skip_regular_prompts = False
        if images_dir.exists() and images_dir.is_dir():
            image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
            existing_images = [f for f in images_dir.iterdir() if f.is_file() and f.suffix.lower() in image_extensions]
            
            if len(existing_images) >= len(raw_prompts):
                skip_regular_prompts = True
                # Check if thumbnail also exists if we need it
                thumbnail_exists = (folder / "thumbnail.jpg").exists()
                if not thumbnail_prompt_text or thumbnail_exists:
                    # Everything is done
                    if project_json_file.exists():
                        try:
                            meta["stage"] = "IMAGES_READY"
                            meta["status"] = "COMPLETED"
                            project_json_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                        except Exception:
                            pass
                    return False, f"{folder.name} (Already fully generated)"

"""
    return new_logic + model_name

new_content = re.sub(import_project_pattern, replacement, content, flags=re.DOTALL)

# Then we also need to change the loop for regular prompts to only run if not skipped,
# and append the thumbnail job.

loop_pattern = r"""(        for p_idx, p_text in enumerate\(raw_prompts\):
            j = Job\(
                id=str\(uuid.uuid4\(\)\),
                topic_name=topic_name,
                topic_slug=slugify\(topic_name\),
                topic_index=len\(jobs\) \+ 1,
                prompt_text=p_text.*?
                project_folder=str\(folder\)
            \)
            jobs\.append\(j\)
            start_global_idx \+= 1)
            
        return True,"""

def loop_replacement(m):
    orig = m.group(1)
    
    # indent the original loop
    indented = "\n".join("    " + line if line.strip() else line for line in orig.split("\n"))
    
    new_loop = f"""        if not skip_regular_prompts:
{indented}

        if thumbnail_prompt_text and not (folder / "thumbnail.jpg").exists():
            tj = Job(
                id=str(uuid.uuid4()),
                topic_name=topic_name,
                topic_slug="thumbnail",
                topic_index=len(jobs) + 1,
                prompt_text=thumbnail_prompt_text,
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
            jobs.append(tj)
            start_global_idx += 1

        return True,"""
    return new_loop

new_content = re.sub(loop_pattern, loop_replacement, new_content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("Updated successfully")
