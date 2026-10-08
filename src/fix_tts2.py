from pathlib import Path

p = Path("H:/Automation/TTS/core/file_handler.py")
content = p.read_text(encoding="utf-8")

replacement = """        valid_folders = []
        for subdir in master_path.iterdir():
            if not subdir.is_dir():
                continue

            project_json = subdir / "project.json"
            if not project_json.exists():
                project_json = subdir / "metadata.json"
                
            script_txt = subdir / "script.txt"

            if not project_json.exists() or not script_txt.exists():
                continue

            try:
                data = json.loads(read_text_file(str(project_json)))"""

target = """        valid_folders = []
        for subdir in master_path.iterdir():
            if not subdir.is_dir():
                continue

            project_json = subdir / "project.json"
            script_txt = subdir / "script.txt"

            if not project_json.exists() or not script_txt.exists():
                continue

            try:
                data = json.loads(read_text_file(str(project_json)))"""



if target in content:
    content = content.replace(target, replacement)
    p.write_text(content, encoding="utf-8")
    print("TTS 2 file patched.")
else:
    print("Could not find target block.")

