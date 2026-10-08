with open(r"H:\Automation\Image Automation\worker.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update worker.py to handle "thumbnail" index
find_str = """        if job.project_folder:
            img_dir = Path(job.project_folder) / "images"
            img_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{job.prompt_index:02d}.png"
            save_path = img_dir / filename
        else:"""

repl_str = """        if job.project_folder:
            if getattr(job, 'prompt_index', 0) == -1 or "thumbnail" in str(getattr(job, 'prompt_slug', '')).lower() or getattr(job, 'topic_slug', '') == 'thumbnail':
                # Generate thumbnail.jpg in project root
                img_dir = Path(job.project_folder)
                img_dir.mkdir(parents=True, exist_ok=True)
                filename = "thumbnail.jpg"
                save_path = img_dir / filename
            else:
                img_dir = Path(job.project_folder) / "images"
                img_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{job.prompt_index:02d}.png"
                save_path = img_dir / filename
        else:"""
if find_str in content:
    content = content.replace(find_str, repl_str)
else:
    print("Could not find replacement string")

with open(r"H:\Automation\Image Automation\worker.py", "w", encoding="utf-8") as f:
    f.write(content)
print("worker fixed")
