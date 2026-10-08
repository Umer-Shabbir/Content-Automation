import re
with open(r"H:\Automation\Image Automation\backend\app\routers\queue.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r"""        # Validation logic to skip if images directory is fully populated"""
replacement = """
        # Check for thumbnail prompt
        thumbnail_prompt_file = folder / "thumbnail_prompt.txt"
        thumbnail_prompt_text = ""
        if thumbnail_prompt_file.exists():
            thumbnail_prompt_text = thumbnail_prompt_file.read_text(encoding="utf-8").strip()

        # Validation logic to skip if images directory is fully populated"""
content = re.sub(pattern, replacement, content, count=1)

pattern2 = r"""        if not skip_regular_prompts:
            for p_idx, p_text in enumerate\(raw_prompts\):
                j = Job\(
                    id=str\(uuid.uuid4\(\)\),
                    topic_name=topic_name,
                    topic_slug=slugify\(topic_name\),
                    topic_index=len\(jobs\) \+ 1,
                    prompt_text=p_text,
                    prompt_index=p_idx \+ 1,
                    global_index=start_global_idx,
                    prompt_slug=slugify\(p_text\[:40\]\),
                    status=JobStatus.PENDING,
                    character_name=char_name,
                    model_name=model_name,
                    mode=mode,
                    aspect_ratio=ar,
                    project_folder=str\(folder\)
                \)
                jobs.append\(j\)
                start_global_idx \+= 1"""
                
replacement2 = """        if not skip_regular_prompts:
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
            start_global_idx += 1"""
content = re.sub(pattern2, replacement2, content, count=1)

with open(r"H:\Automation\Image Automation\backend\app\routers\queue.py", "w", encoding="utf-8") as f:
    f.write(content)
