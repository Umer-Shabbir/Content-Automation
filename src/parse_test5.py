from config.settings import VOICE_CATALOGUE

def parse_speaker_tags(text: str, default_voice: str):
    import re
    pattern = r'(?m)(?:^|\s+)\[([^\]]+)\]\s*'
    parts = re.split(pattern, text)
    
    segments = []
    
    if parts[0].strip():
        segments.append((default_voice, parts[0].strip(), None))
        
    assigned_voices = {}
    available_voices = list(VOICE_CATALOGUE.keys())
    try:
        next_voice_idx = available_voices.index(default_voice)
    except ValueError:
        next_voice_idx = 0
        
    for i in range(1, len(parts), 2):
        raw_tag = parts[i].strip()
        tag_lower = raw_tag.lower()
        
        resolved = None
        for name, cfg in VOICE_CATALOGUE.items():
            if tag_lower == name.lower() or tag_lower == cfg["id"].lower() or tag_lower == name.split("·")[0].strip().lower():
                resolved = name
                break
        
        if not resolved:
            if raw_tag in assigned_voices:
                resolved = assigned_voices[raw_tag]
            else:
                resolved = available_voices[next_voice_idx % len(available_voices)]
                assigned_voices[raw_tag] = resolved
                next_voice_idx += 1
                
        segment_text = parts[i+1].strip() if i+1 < len(parts) else ""
        if segment_text:
            segments.append((resolved, segment_text, raw_tag))
            
    return segments

text = "[af_heart] Hello. [Speaker B] General Kenobi. [Speaker B] You are a bold one."
print(parse_speaker_tags(text, "Heart  ·  American Female"))
