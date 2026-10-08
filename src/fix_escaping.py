import re
with open("H:/Automation/Video Forge/app/subtitles/styler.py", "r", encoding="utf-8") as f:
    text = f.read()

# Fix broken ASS escaping from previous replace
text = text.replace("{\1c&H{spk_color}&}\b1{chunk.speaker}:\b0 ", "{\\1c&H{spk_color}&}\\b1{chunk.speaker}:\\b0 ")
text = text.replace("{\1c&H{chunk_normal_bbggrr}&}\b1{chunk.speaker}:\b0 ", "{\\1c&H{chunk_normal_bbggrr}&}\\b1{chunk.speaker}:\\b0 ")

with open("H:/Automation/Video Forge/app/subtitles/styler.py", "w", encoding="utf-8") as f:
    f.write(text)
