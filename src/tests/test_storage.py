import pytest
import os
import shutil
import json
from pathlib import Path

from app.storage.sanitizer import sanitize_filename, sanitize_windows_filename, sanitize_path
from app.storage.exporter import ContentExporter
from app.models.generation import GenerationPackage, ScenePrompt, VisualContinuityState

# ----------------- Sanitizer Tests -----------------

def test_sanitizer_illegal_chars():
    # Characters: < > : " / \ | ? *
    bad_name = 'My: Cool <Video> / Title "Test" | * ?'
    clean = sanitize_filename(bad_name)
    assert ":" not in clean
    assert "<" not in clean
    assert ">" not in clean
    assert "/" not in clean
    assert "\\" not in clean
    assert '"' not in clean
    assert "|" not in clean
    assert "*" not in clean
    assert "?" not in clean

def test_sanitizer_reserved_names():
    reserved = ["CON", "prn", "AUX.txt", "Nul", "COM1", "lpt9"]
    for r in reserved:
        clean = sanitize_filename(r)
        assert clean.upper() != r.upper()
        assert clean.startswith("safe_") or clean.endswith("_safename")

def test_sanitizer_traversal():
    traversal = "../../etc/passwd"
    clean = sanitize_filename(traversal)
    assert ".." not in clean
    assert "/" not in clean
    assert "\\" not in clean

def test_sanitizer_truncation():
    very_long = "a" * 300 + ".txt"
    clean = sanitize_filename(very_long, max_length=50)
    assert len(clean) <= 50

def test_sanitizer_empty_and_fallback():
    assert sanitize_filename("") in ("untitled", "output")
    assert sanitize_filename("   ...  ") in ("untitled", "output")
    assert sanitize_filename("???***") in ("untitled", "output")

def test_sanitize_path():
    res = sanitize_path('folder/file.txt')
    assert res == os.path.normpath('folder/file.txt')

    with pytest.raises(ValueError, match="Directory traversal attempt detected in path"):
        sanitize_path('../folder/file.txt')

    with pytest.raises(ValueError, match="Directory traversal attempt detected in path"):
        sanitize_path('folder/../../file.txt')


# ----------------- Exporter Tests -----------------

@pytest.fixture
def temp_output_dir(tmp_path):
    output_dir = tmp_path / "export_test"
    output_dir.mkdir()
    yield output_dir
    # Cleanup
    shutil.rmtree(output_dir, ignore_errors=True)

@pytest.fixture
def sample_package():
    return GenerationPackage(
        topic="AI Revolution",
        preset_name="Tech_Default",
        title="The Future of AI: What's Next?",
        normalized_title="the-future-of-ai-whats-next",
        script="This is the full script of the generation.",
        prompts=[
            ScenePrompt(
                scene_number=1,
                narration_segment="Scene 1 text",
                visual_description="A futuristic lab",
                detailed_image_prompt="High detail 8k render of a futuristic lab"
            ),
            ScenePrompt(
                scene_number=2,
                narration_segment="Scene 2 text",
                visual_description="A robot working",
                detailed_image_prompt="A sleek modern robot typing on a holographic keyboard"
            )
        ],
        continuity=VisualContinuityState(
            art_style_anchor="Cinematic sci-fi style"
        ),
        total_words=20,
        estimated_duration_sec=10.5,
        quality_score=0.95,
        reviewer_notes="Looks solid."
    )

def test_exporter_creates_files(temp_output_dir, sample_package):
    export_path = ContentExporter.export_package(sample_package, base_output_dir=str(temp_output_dir), include_metadata=True)

    path = Path(export_path)
    assert path.exists()
    assert path.is_dir()

    # Check individual files
    assert (path / "title.txt").exists()
    assert (path / "title.txt").read_text(encoding="utf-8") == sample_package.title

    assert (path / "script.txt").exists()
    assert (path / "script.txt").read_text(encoding="utf-8") == sample_package.script

    assert (path / "prompts.txt").exists()
    prompts_content = (path / "prompts.txt").read_text(encoding="utf-8")
    assert "SCENE 1" in prompts_content
    assert "High detail 8k render" in prompts_content
    assert "SCENE 2" in prompts_content

    assert (path / "metadata.json").exists()
    metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["title"] == sample_package.title
    assert metadata["quality_score"] == 0.95

def test_exporter_no_metadata(temp_output_dir, sample_package):
    export_path = ContentExporter.export_package(sample_package, base_output_dir=str(temp_output_dir), include_metadata=False)

    path = Path(export_path)
    assert (path / "title.txt").exists()
    assert not (path / "metadata.json").exists()

def test_exporter_collision_handling(temp_output_dir, sample_package):
    # First export
    path1 = ContentExporter.export_package(sample_package, base_output_dir=str(temp_output_dir))
    # Second export with same title
    path2 = ContentExporter.export_package(sample_package, base_output_dir=str(temp_output_dir))
    # Third export with same title
    path3 = ContentExporter.export_package(sample_package, base_output_dir=str(temp_output_dir))

    p1, p2, p3 = Path(path1), Path(path2), Path(path3)

    assert p1.exists()
    assert p2.exists()
    assert p3.exists()

    assert p1.name == "the-future-of-ai-whats-next"
    assert p2.name == "the-future-of-ai-whats-next (1)"
    assert p3.name == "the-future-of-ai-whats-next (2)"

def test_exporter_instance_method(temp_output_dir, sample_package):
    exporter = ContentExporter(base_output_dir=str(temp_output_dir))
    export_path = exporter.export(sample_package)
    p = Path(export_path)
    assert p.exists()
    assert p.is_dir()
