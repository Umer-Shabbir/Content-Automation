import pytest
from app.models.preset import ContentPreset, load_builtin_presets, ScriptRules
from app.prompts.parser import extract_chapters_from_script
from app.pipeline.stages.script_stage import sanitize_voiceover_script
from app.storage.exporter import ContentExporter
from app.models.generation import GenerationPackage

def test_all_builtin_presets_have_chapter_narrative_structure():
    presets = load_builtin_presets()
    assert len(presets) >= 11
    for name, preset in presets.items():
        assert hasattr(preset, "script_rules"), f"{name} missing script_rules"
        assert "chapter" in preset.script_rules.narrative_structure.lower(), (
            f"Preset {name} narrative_structure does not contain chapter-based writing: {preset.script_rules.narrative_structure}"
        )
        assert getattr(preset.script_rules, "chapter_format", None) == "[Chapter: <Title>]"

def test_extract_chapters_from_script():
    script = """
[Chapter: The Midnight Heist]
At three in the morning, inside the quiet facility, the alarm silently tripped.
Nobody knew that the system had been breached.

[Chapter: The Hidden Network]
To understand how they did it, you have to trace the analog signals.
Long before fiber optics connected cities, cables were tapped.

[Chapter: The Showdown]
Finally, federal agents surrounded the perimeter.
    """
    chapters = extract_chapters_from_script(script)
    assert len(chapters) == 3
    assert chapters[0]["title"] == "The Midnight Heist"
    assert "At three in the morning" in chapters[0]["first_sentence"]
    assert chapters[1]["title"] == "The Hidden Network"
    assert "To understand how they did it" in chapters[1]["first_sentence"]
    assert chapters[2]["title"] == "The Showdown"

def test_sanitize_voiceover_script_preserves_chapters():
    raw_script = """
[Narrator]
[Music: Dramatic intro]
[Chapter: The Breakthrough]
(pause)
Here is what happened next.
[Sound effect: Thunder]
The experiment succeeded.
    """
    cleaned = sanitize_voiceover_script(raw_script)
    assert "[Chapter: The Breakthrough]" in cleaned
    assert "[Narrator]" not in cleaned
    assert "[Music" not in cleaned
    assert "(pause)" not in cleaned
    assert "[Sound effect" not in cleaned
    assert "The experiment succeeded" in cleaned

def test_content_exporter_writes_chapters(tmp_path):
    pkg = GenerationPackage(
        topic="Analog Network",
        preset_name="punk_zine",
        title="The Stolen Ink Revolt",
        normalized_title="the_stolen_ink_revolt",
        script="[Chapter: The Origin]\nIn 1981, culture was a fortress.\n\n[Chapter: The Rebellion]\nThey hacked the copy machines.",
        prompts=[]
    )
    preset = ContentPreset(name="punk_zine")
    out_dir = ContentExporter.export_package(pkg, base_output_dir=str(tmp_path), preset=preset)
    
    chapters_txt = tmp_path / "the_stolen_ink_revolt" / "chapters.txt"
    assert chapters_txt.exists()
    content = chapters_txt.read_text(encoding="utf-8")
    assert "00:00 - The Origin" in content
    assert "The Rebellion" in content

    project_json = tmp_path / "the_stolen_ink_revolt" / "project.json"
    assert project_json.exists()
    import json
    data = json.loads(project_json.read_text(encoding="utf-8"))
    assert "chapters" in data
    assert len(data["chapters"]) == 2
    assert data["chapters"][0]["title"] == "The Origin"
