with open(r"H:\Automation\Image Automation\backend\app\routers\queue.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.strip() == "# Parse thumbnail_prompt.txt if it exists":
        skip = True
    if line.strip() == "# Parse prompts.txt to determine how many lines there are":
        skip = False

    if line.strip() == "# Check for thumbnail prompt":
        skip = True
    if line.strip() == "# Validation logic to skip if images directory is fully populated":
        skip = False
        
    if line.strip() == "if thumbnail_prompt:":
        skip = True
    if line.strip() == 'return True, ""' and skip:
        skip = False
    
    if not skip:
        new_lines.append(line)

new_content = "".join(new_lines)
with open(r"H:\Automation\Image Automation\backend\app\routers\queue.py", "w", encoding="utf-8") as f:
    f.write(new_content)
