import pytest
import json
from pathlib import Path
from app.models.preset import BUILTIN_PRESETS, ContentPreset, ThumbnailStyle
from app.models.generation import GenerationPackage, VisualContinuityState
from app.storage.exporter import ContentExporter
from app.prompts.builder import PromptBuilder

def test_all_builtin_presets_have_3_thumbnail_styles():
    assert len(BUILTIN_PRESETS) >= 10
    for name, preset in BUILTIN_PRESETS.items():
        assert len(preset.thumbnail_styles) == 3, f"Preset {name} must have exactly 3 thumbnail styles"
        ids = [s.id for s in preset.thumbnail_styles]
        assert len(set(ids)) == 3, f"Preset {name} styles must have distinct IDs: {ids}"
        names = [s.name for s in preset.thumbnail_styles]
        assert len(set(names)) == 3, f"Preset {name} styles must have distinct names: {names}"
        for s in preset.thumbnail_styles:
            assert len(s.description.strip()) > 20, f"Style {s.name} in {name} must have detailed guidelines"

def test_exporter_generates_3_thumbnail_prompts(tmp_path):
    preset = BUILTIN_PRESETS.get("blueprint", ContentPreset(name="blueprint"))
    pkg = GenerationPackage(
        topic="The Engineering of the Golden Gate Bridge",
        preset_name="blueprint",
        title="Why the Golden Gate Bridge Should Have Been Impossible to Build",
        normalized_title="why_the_golden_gate_bridge_should_have_been_impossible_to_build",
        script="A gripping story of suspension bridge physics and ocean currents.",
        prompts=[],
        continuity=VisualContinuityState(art_style_anchor="engineering blueprint style")
    )

    out_dir = ContentExporter.export_package(pkg, base_output_dir=str(tmp_path), preset=preset)
    proj_dir = Path(out_dir)

    # 1. Check thumbnail_prompt.txt contains all 3 thumbnail prompts
    thumb_txt = (proj_dir / "thumbnail_prompt.txt").read_text(encoding="utf-8")
    assert "--- Thumbnail Style 1:" in thumb_txt
    assert "--- Thumbnail Style 2:" in thumb_txt
    assert "--- Thumbnail Style 3:" in thumb_txt
    # All 3 prompt markers
    assert thumb_txt.count("Thumbnail Prompt:") == 3

    # 2. Check project.json contains thumbnail_prompts list
    pjson = json.loads((proj_dir / "project.json").read_text(encoding="utf-8"))
    assert "thumbnail_prompts" in pjson
    assert len(pjson["thumbnail_prompts"]) == 3
    for tp in pjson["thumbnail_prompts"]:
        assert "style_id" in tp
        assert "style_name" in tp
        assert "prompt" in tp
        assert len(tp["prompt"]) > 30

def test_builder_thumbnail_prompts_message():
    preset = BUILTIN_PRESETS.get("clay", ContentPreset(name="clay"))
    payload = PromptBuilder.build_thumbnail_prompts_messages(
        topic="Habit Formation",
        title="Atomic Habits Explained",
        preset=preset,
        art_style_anchor="pastel clay 3D render"
    )
    assert "system" in payload
    assert len(payload["messages"]) == 1
    content = payload["messages"][0]["content"]
    assert "Atomic Habits Explained" in content
    assert "Style 1" in content
    assert "Style 2" in content
    assert "Style 3" in content
