from config.settings import VOICE_CATALOGUE

def resolve_voice(tag: str, default_voice: str):
    tag = tag.strip().lower()
    for name, cfg in VOICE_CATALOGUE.items():
        if tag == name.lower() or tag == cfg["id"].lower() or tag == name.split("·")[0].strip().lower():
            return name
    return default_voice

print(resolve_voice("af_heart", "Default"))
print(resolve_voice("Heart", "Default"))
print(resolve_voice("Bella  ·  American Female", "Default"))
print(resolve_voice("Unknown", "Default"))
