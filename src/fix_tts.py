from pathlib import Path

p = Path("H:/Automation/TTS/core/file_handler.py")
content = p.read_text(encoding="utf-8")

replacement = """        valid_folders = []
        for subdir in base_path.iterdir():
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

# Regex replacing the old block
import re
content = re.sub(r"valid_folders = \[\]\s+for subdir in base_path\.iterdir\(\):\s+if not subdir\.is_dir\(\):\s+continue\s+project_json = subdir / \"project\.json\"\s+script_txt = subdir / \"script\.txt\"\s+if not project_json\.exists\(\) or not script_txt\.exists\(\):\s+continue\s+try:\s+data = json\.loads\(read_text_file\(str\(project_json\)\)\)", replacement, content, flags=re.MULTILINE|re.DOTALL)

p.write_text(content, encoding="utf-8")
print("TTS file patched.")

