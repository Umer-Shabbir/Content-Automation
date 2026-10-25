import pytest
import tempfile
import os
from pathlib import Path
from app.db.database import DatabaseCoordinator
from app.db.idea_manager import IdeaManager, normalize_topic_string, extract_keywords
from app.models.preset import ContentPreset


@pytest.fixture
def temp_idea_manager(tmp_path):
    db_path = str(tmp_path / "test_ideas.db")
    db_coord = DatabaseCoordinator(db_path=db_path)
    mgr = IdeaManager(db_coordinator=db_coord)
    mgr.initialize(extra_scan_dirs=[])
    return mgr


def test_normalization_and_keywords():
    assert normalize_topic_string("The Fall of Rome!") == "the fall of rome"
    assert normalize_topic_string("The-Engineering_of_The Golden Gate Bridge") == "the engineering of the golden gate bridge"

    kws = extract_keywords("The Engineering of the Golden Gate Bridge")
    assert "golden" in kws
    assert "gate" in kws
    assert "bridge" in kws
    assert "engineering" in kws
    assert "the" not in kws
    assert "of" not in kws


def test_golden_gate_bridge_and_y2k_never_repeated(temp_idea_manager):
    mgr = temp_idea_manager

    # Record historical topics
    mgr.complete_idea(
        topic="The Engineering of the Golden Gate Bridge",
        title="Why 1930s Engineers Were Convinced The Golden Gate Bridge Would Collapse",
        preset_name="blueprint"
    )
    mgr.complete_idea(
        topic="The Y2K Bug Code Remediation Effort",
        title="The 100 Billion Bug Fix That Saved The Modern World",
        preset_name="phosphor_terminal"
    )

    # Exact checks
    assert mgr.is_idea_generated("The Engineering of the Golden Gate Bridge") is True
    assert mgr.is_idea_generated("The Y2K Bug Code Remediation Effort") is True

    # Variations & sub-phrases (e.g. user entering "golden gate bridge" or "y2k bug")
    assert mgr.is_idea_generated("golden gate bridge") is True
    assert mgr.is_idea_generated("Golden Gate Bridge") is True
    assert mgr.is_idea_generated("y2k bug") is True
    assert mgr.is_idea_generated("The Y2K Bug") is True
    assert mgr.is_idea_generated("Y2K Bug Code Remediation") is True

    # Different topic should NOT match
    assert mgr.is_idea_generated("The Construction of the Empire State Building") is False
    assert mgr.is_idea_generated("Quantum Computing Breakthroughs") is False


def test_get_next_topics_for_preset_skips_generated(temp_idea_manager):
    mgr = temp_idea_manager

    preset = ContentPreset(
        name="test_preset",
        niche_topics=[
            "The Engineering of the Golden Gate Bridge",
            "The Hoover Dam: Concrete, Pressure, and Triumph",
            "The Panama Canal: Cutting the Earth in Two"
        ]
    )

    # First, mark the first topic as already generated
    mgr.complete_idea(
        topic="The Engineering of the Golden Gate Bridge",
        title="Golden Gate Story",
        preset_name="test_preset"
    )

    # Now ask for 1 topic - it MUST NOT return Golden Gate Bridge, it must return Hoover Dam!
    next_topics = mgr.get_next_topics_for_preset("test_preset", preset, count=1)
    assert len(next_topics) == 1
    assert next_topics[0] == "The Hoover Dam: Concrete, Pressure, and Triumph"

    # Now asking again should give the 3rd topic (Panama Canal)
    next_topics_2 = mgr.get_next_topics_for_preset("test_preset", preset, count=1)
    assert len(next_topics_2) == 1
    assert next_topics_2[0] == "The Panama Canal: Cutting the Earth in Two"


def test_reserve_idea_prevents_duplicate_reservations(temp_idea_manager):
    mgr = temp_idea_manager

    # First reservation succeeds
    success1 = mgr.reserve_idea("test_preset", "The Apollo 11 Guidance Computer")
    assert success1 is True

    # Immediate second reservation of the same idea fails
    success2 = mgr.reserve_idea("test_preset", "The Apollo 11 Guidance Computer")
    assert success2 is False


def test_disk_scan_syncing(temp_idea_manager, tmp_path):
    mgr = temp_idea_manager

    # Create dummy project folders on disk
    proj1 = tmp_path / "project_one"
    proj1.mkdir()
    (proj1 / "project.json").write_text(
        '{"topic": "Ancient Rome Concrete Secrets", "title": "Why Roman Concrete Lasts 2000 Years", "preset": "history"}',
        encoding="utf-8"
    )

    proj2 = tmp_path / "voynich_manuscript_mystery"
    proj2.mkdir()
    (proj2 / "project.json").write_text(
        '{"topic": "The Mystery of the Undeciphered Voynich Manuscript", "title": "The Book No One Can Read", "preset": "mystery"}',
        encoding="utf-8"
    )

    # Run disk scan
    mgr._sync_default_disk_directories(extra_dirs=[str(tmp_path)])

    # Verify both are now recognized as generated
    assert mgr.is_idea_generated("Ancient Rome Concrete Secrets") is True
    assert mgr.is_idea_generated("Roman Concrete Lasts") is True
    assert mgr.is_idea_generated("The Mystery of the Undeciphered Voynich Manuscript") is True
    assert mgr.is_idea_generated("voynich manuscript") is True
