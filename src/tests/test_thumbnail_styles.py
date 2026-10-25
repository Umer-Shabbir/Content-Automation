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


def test_builder_thumbnail_critic_message():
    preset = BUILTIN_PRESETS.get("clay", ContentPreset(name="clay"))
    candidates = [
        {"style_id": "clay_hero", "style_name": "Hero Subject", "thumbnail_prompt": "Clay character looking at giant hourglass"}
    ]
    payload = PromptBuilder.build_thumbnail_critic_messages(
        topic="Habit Formation",
        title="Atomic Habits Explained",
        candidates=candidates,
        preset=preset,
        art_style_anchor="pastel clay 3D render"
    )
    assert "system" in payload
    assert len(payload["messages"]) == 1
    content = payload["messages"][0]["content"]
    assert "Atomic Habits Explained" in content
    assert "clay_hero" in content


@pytest.mark.asyncio
async def test_thumbnail_stage_two_step_generator_and_critic():
    from unittest.mock import AsyncMock
    from app.ai.client import AnthropicClient
    from app.pipeline.stages.thumbnail_stage import ThumbnailStage

    mock_ai = AsyncMock(spec=AnthropicClient)

    calls = []
    async def mock_generate_message(messages, system=None):
        calls.append({"messages": messages, "system": system})
        content = messages[0]["content"]
        if "Candidate Prompts:" in content:
            # Critic call
            return {
                "text": json.dumps({
                    "decision": "APPROVE",
                    "overall_score": 95,
                    "critique": "Solid focal separation and curiosity hook.",
                    "evaluated_thumbnails": [
                        {"style_id": "style_1", "refined_prompt": "Refined cinematic hero prompt with text: 'DO NOT' in background"},
                        {"style_id": "style_2", "refined_prompt": "Refined cinematic dynamic action prompt"},
                        {"style_id": "style_3", "refined_prompt": "Refined cinematic macro detail prompt"}
                    ]
                })
            }
        else:
            # Candidate generation call
            return {
                "text": json.dumps([
                    {"style_id": "style_1", "style_name": "Hero", "thumbnail_prompt": "Raw candidate 1"},
                    {"style_id": "style_2", "style_name": "Action", "thumbnail_prompt": "Raw candidate 2"},
                    {"style_id": "style_3", "style_name": "Macro", "thumbnail_prompt": "Raw candidate 3"}
                ])
            }

    mock_ai.generate_message.side_effect = mock_generate_message

    stage = ThumbnailStage(ai_client=mock_ai)
    preset = BUILTIN_PRESETS.get("blueprint", ContentPreset(name="blueprint"))
    pkg = GenerationPackage(
        topic="Quantum Engines",
        preset_name="blueprint",
        title="The Engine That Defies Physics",
        normalized_title="the_engine_that_defies_physics",
        script="A deep dive into quantum thermodynamics.",
        prompts=[]
    )

    refined_prompts = await stage.process(pkg, preset)

    assert len(refined_prompts) == 3
    # Check that both generator and critic were called
    assert len(calls) == 2
    # Verify zero-text rule stripped the text instruction
    assert "text: 'DO NOT'" not in refined_prompts[0]
    # Verify style anchor was locked
    for p in refined_prompts:
        assert "Blueprint architectural schematic" in p or "blueprint" in p.lower()


def test_all_11_presets_have_bespoke_unique_thumbnail_styles():
    """Verify that all 11 presets exist and have bespoke, non-generic thumbnail styles."""
    expected_presets = [
        "blueprint", "clay", "cobalt_impact", "cutout_collage", "glass_node",
        "line_graphic", "paint_blast", "paper_glass", "phosphor_terminal",
        "punk_zine", "money_chuck"
    ]
    for p_name in expected_presets:
        assert p_name in BUILTIN_PRESETS, f"Preset {p_name} must be in BUILTIN_PRESETS"
        preset = BUILTIN_PRESETS[p_name]
        assert len(preset.thumbnail_styles) == 3, f"Preset {p_name} must have exactly 3 thumbnail styles"
        for s in preset.thumbnail_styles:
            assert len(s.id.strip()) > 3
            assert len(s.name.strip()) > 5
            assert len(s.description.strip()) >= 50, f"Description for {s.name} in {p_name} must be comprehensive"

    # Ensure styles are not generic across different presets
    all_style_ids = []
    all_style_names = []
    for p_name, preset in BUILTIN_PRESETS.items():
        for s in preset.thumbnail_styles:
            all_style_ids.append(s.id)
            all_style_names.append(s.name)

    # Every style ID should be globally unique across all presets
    assert len(all_style_ids) == len(set(all_style_ids)), "Every preset must have distinct, bespoke style IDs (no generic copy-paste)"
    assert len(all_style_names) == len(set(all_style_names)), "Every preset must have distinct, bespoke style names"


def test_money_chuck_stick_figure_thumbnail_styles():
    """Verify money_chuck has tailored doodle/stick-figure styles on pure white void."""
    preset = BUILTIN_PRESETS["money_chuck"]
    ids = [s.id for s in preset.thumbnail_styles]
    assert "smug_billionaire_caricature" in ids
    assert "cliff_collapse_40b" in ids
    assert "smoke_and_mirrors_split" in ids

    # Check descriptions mention stick figure / white background / doodle
    for s in preset.thumbnail_styles:
        desc_lower = s.description.lower()
        assert "stick-figure" in desc_lower or "doodle" in desc_lower
        assert "white" in desc_lower
        assert "no text" in desc_lower


def test_zero_text_cleaning_advanced():
    """Test advanced regex stripping of text instructions in ThumbnailStage."""
    from app.pipeline.stages.thumbnail_stage import ThumbnailStage
    stage = ThumbnailStage(ai_client=None)

    dirty_prompts = [
        "Hero stick figure screaming, with text 'TOTAL FAILURE' in bold red",
        "Curved CRT monitor showing the words 'ACCESS DENIED' on screen",
        "Declassified folder with signage reading 'TOP SECRET' across top",
        "A colossal machine with headline: 'THE COLLAPSE' floating above",
        "Tactile clay figure with label: 'ANXIETY' stamped on chest",
    ]

    for dirty in dirty_prompts:
        cleaned = stage._enforce_thumbnail_rules(dirty, anchor="minimalist style")
        assert "TOTAL FAILURE" not in cleaned
        assert "ACCESS DENIED" not in cleaned
        assert "TOP SECRET" not in cleaned
        assert "THE COLLAPSE" not in cleaned
        assert "ANXIETY" not in cleaned
        assert "minimalist style" in cleaned


def test_exporter_fallback_prompts_for_all_presets(tmp_path):
    """Test that ContentExporter produces rich, methodology-grounded prompts for multiple presets."""
    test_presets = ["blueprint", "clay", "phosphor_terminal", "money_chuck", "cobalt_impact"]
    for p_name in test_presets:
        preset = BUILTIN_PRESETS[p_name]
        pkg = GenerationPackage(
            topic=f"Testing {p_name}",
            preset_name=p_name,
            title=f"The Great Mystery of {p_name.title()}",
            normalized_title=f"the_great_mystery_of_{p_name}",
            script="Narration text here.",
            prompts=[]
        )
        prompts_data = ContentExporter._get_or_generate_thumbnail_prompts(pkg, preset=preset)
        assert len(prompts_data) == 3
        for item in prompts_data:
            p = item["prompt"]
            # Must mention high-CTR and 3-Element rule / focal dominance
            assert "high-CTR" in p
            assert "3-Element rule" in p
            assert "focal subject" in p
            assert "No text" in p
            assert len(p) > 100


