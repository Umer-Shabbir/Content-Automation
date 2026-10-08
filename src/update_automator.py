import re

with open(r"H:\Automation\Image Automation\models.py", "r") as f:
    content = f.read()

# Make ImageCount logic simpler
if "COUNT_9=" not in content:
    content = content.replace('    COUNT_4 = "x4"', '    COUNT_4 = "x4"\n    COUNT_ALL = "all"')
    content = content.replace('    ALL = [COUNT_1, COUNT_2, COUNT_3, COUNT_4]', '    ALL = [COUNT_1, COUNT_2, COUNT_3, COUNT_4, COUNT_ALL]')

with open(r"H:\Automation\Image Automation\models.py", "w") as f:
    f.write(content)

with open(r"H:\Automation\Image Automation\automator.py", "r") as f:
    content = f.read()

# If thumbnail_prompt.txt is passed in prompt_text logic 
# wait, actually we want to change worker.py, not automator.py. Wait no, automator handles the downloads.
# In worker.py, we only download if there's a thumbnail. Let's see worker.py next.
