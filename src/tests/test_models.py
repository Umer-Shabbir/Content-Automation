import pytest
from app.models.enums import JobState, ReviewDecision, LogLevel
from app.models.api_profile import APIProfile, RequestConfig
from app.models.preset import ContentPreset, TitleRules, ScriptRules, ImageRules, ReviewerRules
from app.models.generation import GenerationPackage, ScenePrompt, VisualContinuityState
from app.models.job import Job, Batch, StageMetric, JobProgress

def test_enums():
    assert JobState.QUEUED.value == "QUEUED"
    assert ReviewDecision.APPROVE.value == "APPROVE"
    assert LogLevel.DEBUG.value == "DEBUG"

def test_api_profile_validation():
    # Valid
    config = RequestConfig()
    profile = APIProfile(
        id="123",
        name="Test",
        base_url="https://api.test.com/v1",
        api_key="secret-key-123",
        model="claude-3-haiku-20240307",
        config=config
    )
    assert profile.get_api_key() == "secret-key-123"
    assert profile.api_key.get_secret_value() == "secret-key-123"
    assert "secret-key-123" not in repr(profile)
    assert "APIProfile" in repr(profile)

    # Invalid URL
    with pytest.raises(ValueError):
        APIProfile(name="T", base_url="ftp://bad.com", api_key="s", model="m")

def test_preset_models():
    preset = ContentPreset(
        name="History Drama",
        is_builtin=True,
    )
    assert preset.title_rules.curiosity_level == 9
    assert preset.script_rules.target_duration_minutes == 10
    assert preset.image_rules.aspect_ratio == "16:9"

def test_preset_niche_topics():
    preset = ContentPreset(
        name="test_niche",
        niche_topics=["Topic A", "Topic B", "Topic C"]
    )
    assert preset.get_topic(0) == "Topic A"
    assert preset.get_topic(1) == "Topic B"
    assert preset.get_topic(2) == "Topic C"
    # Cycling test
    assert preset.get_topic(3) == "Topic A"

    # Fallback test
    empty_preset = ContentPreset(name="tech_news", niche_topics=[])
    assert empty_preset.get_topic(0) == "Tech News Story"


def test_generation_models():
    scene = ScenePrompt(
        scene_number=1,
        narration_segment="Once upon a time",
        visual_description="A castle",
        detailed_image_prompt="A majestic castle at golden hour, 8k, cinematic"
    )
    pkg = GenerationPackage(
        topic="Castles",
        preset_name="test",
        title="The Castle",
        normalized_title="the castle",
        script="Once upon a time. The end.",
        prompts=[scene]
    )
    assert pkg.topic == "Castles"
    assert len(pkg.prompts) == 1

def test_job_models():
    job = Job(
        id="j-123",
        batch_id="b-456",
        topic="Rome",
        preset_id="p-1",
        preset_name="History"
    )
    assert job.status == JobState.QUEUED
    assert isinstance(job.metrics, list)