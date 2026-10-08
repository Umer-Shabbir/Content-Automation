import re
text = "[af_heart] Hello, how are you? [am_adam] I am fine, thank you! [af_kore] What about you?"
tag_map = {"af_heart": "Heart", "am_adam": "Adam"}
pattern = r'\[(.*?)\]'
parts = re.split(pattern, text)
segments = []
curr_voice = "Default"
if parts[0].strip():
    segments.append((curr_voice, parts[0].strip()))
for i in range(1, len(parts), 2):
    tag = parts[i].strip()
    tag_lower = tag.lower()
    curr_voice = tag_map.get(tag_lower, curr_voice)
    text_segment = parts[i+1].strip() if i+1 < len(parts) else ""
    if text_segment:
        segments.append((curr_voice, text_segment))
print(segments)
