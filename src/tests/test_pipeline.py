import pytest
from unittest.mock import AsyncMock, MagicMock
from app.pipeline.pipeline import GenerationPipeline
from app.models.preset import ContentPreset
from app.models.generation import GenerationPackage

@pytest.fixture
def mock_preset():
    return ContentPreset(name="test_preset", output_dir="test_output")

@pytest.fixture
def mock_pipeline():
    title_mock = AsyncMock()
    title_mock.process.return_value = "Test Async Title"

    script_mock = AsyncMock()
    script_mock.process.return_value = "This is a dummy script for testing."

    scene_mock = AsyncMock()
    scene_mock.process.return_value = [
        {"scene_number": 1, "narration_segment": "This is a", "visual_description": "Intro"},
        {"scene_number": 2, "narration_segment": "dummy script.", "visual_description": "Outro"}
    ]

    image_mock = AsyncMock()
    # image_mock process returns (prompts, continuity)
    image_mock.process.return_value = ([], AsyncMock())

    review_mock = AsyncMock()
    review_mock.process.side_effect = lambda pkg: pkg

    pipeline = GenerationPipeline(
        title_stage=title_mock,
        script_stage=script_mock,
        scene_stage=scene_mock,
        image_prompt_stage=image_mock,
        final_review_stage=review_mock
    )
    # Mock exporter
    pipeline.exporter = MagicMock()
    return pipeline

@pytest.mark.asyncio
async def test_generation_pipeline_run(mock_pipeline, mock_preset):
    topic = "Testing pipelines"

    package = await mock_pipeline.run(topic, mock_preset)

    assert isinstance(package, GenerationPackage)
    assert package.topic == topic
    assert package.title == "Test Async Title"
    assert package.normalized_title == "test_async_title"
    assert "dummy script" in package.script
    assert package.total_words == 7

    mock_pipeline.title_stage.process.assert_called_once_with(topic, mock_preset)
    mock_pipeline.script_stage.process.assert_called_once_with(topic, package.title, mock_preset)

