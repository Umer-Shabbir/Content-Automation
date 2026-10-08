import re
with open("H:/Automation/Video Forge/app/subtitles/styler.py", "r", encoding="utf-8") as f:
    text = f.read()

# Add speaker colors definition at the top
colors_block = """
# Fallback colors for speakers when multi-speaker mode is used
SPEAKER_COLORS = [
    "&H00FFFFFF",  # White
    "&H00FFFF00",  # Cyan
    "&H00AAAAFF",  # Light Red/Pink
    "&H00AAFFAA",  # Light Green
    "&H00FFAAFF",  # Magenta
    "&H0000AAFF"   # Orange
]

def _get_speaker_color(speaker: str, profile: RenderProfile) -> str:
    if not speaker:
        return profile.subtitle_primary_color
        
    # Hash the speaker string to always get the same color for same speaker
    import hashlib
    h = int(hashlib.md5(speaker.encode()).hexdigest(), 16)
    idx = h % len(SPEAKER_COLORS)
    return SPEAKER_COLORS[idx]
"""

# Implement modifications to styler.py for karaoke
text = text.replace("events = []\n\n    normal_bbggrr    = _ass_color_to_bbggrr(profile.subtitle_primary_color)\n    highlight_bbggrr = _ass_color_to_bbggrr(profile.subtitle_karaoke_color)", 
"events = []\n\n    def get_normal_bbggrr(chunk_speaker):\n        return _ass_color_to_bbggrr(_get_speaker_color(chunk_speaker, profile))\n\n    highlight_bbggrr = _ass_color_to_bbggrr(profile.subtitle_karaoke_color)")

text = text.replace("normal_tag    = _make_colour_tag(normal_bbggrr)", "# normal_tag is dynamic now")
text = text.replace("    log.debug(\n        f\"Karaoke: normal=&H{normal_bbggrr} \"\n        f\"highlight=&H{highlight_bbggrr}\"\n    )", "    log.debug(f\"Karaoke mode enabled, highlight=&H{highlight_bbggrr}\")")

text = text.replace("normal_bbggrr    ", "normal_bbggrr_default ")

text = text.replace("line_text = _build_karaoke_line(esc_words, i, normal_tag, highlight_tag)", 
"chunk_normal_bbggrr = get_normal_bbggrr(chunk.speaker)\n            normal_tag = _make_colour_tag(chunk_normal_bbggrr)\n            \n            line_text = _build_karaoke_line(esc_words, i, normal_tag, highlight_tag)\n            if chunk.speaker:\n                speaker_label = f\"{\\1c&H{chunk_normal_bbggrr}&}\\b1{chunk.speaker}:\\b0 \"\n                line_text = speaker_label + line_text")

text = text.replace("text = _wrap(_esc(chunk.text), max_chars)", 
"text = _wrap(_esc(chunk.text), max_chars)\n        if chunk.speaker:\n            spk_color = _ass_color_to_bbggrr(_get_speaker_color(chunk.speaker, profile))\n            text = f\"{\\1c&H{spk_color}&}\\b1{chunk.speaker}:\\b0 {text}\"")

with open("H:/Automation/Video Forge/app/subtitles/styler.py", "w", encoding="utf-8") as f:
    f.write(colors_block + text)
