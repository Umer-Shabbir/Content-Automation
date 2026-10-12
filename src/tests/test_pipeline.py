import pytest
from unittest.mock import AsyncMock, MagicMock
from app.pipeline.pipeline import GenerationPipeline, slugify_title
from app.pipeline.stages.title_stage import is_valid_title, clean_title_string, TitleStage
from app.models.preset import ContentPreset
from app.models.generation import GenerationPackage

@pytest.fixture
def mock_preset():
    return ContentPreset(name="test_preset", output_dir="test_output")

@pytest.fixture
def mock_pipeline():
    title_mock = AsyncMock()
    title_mock.process.return_value = ("Test Async Title", ["tag1"], "desc")

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


def test_slugify_title():
    assert slugify_title("The Future of AI: What's Next?") == "the_future_of_ai_whats_next"
    assert slugify_title("(empty_response)[skill_result_memory_search]", topic="AI Ethics") == "project_ai_ethics"
    assert slugify_title("  Title -- with   spaces and punctuation!  ") == "title_with_spaces_and_punctuation"


def test_is_valid_title():
    assert is_valid_title("10 Mind-Blowing Facts About Space") is True
    assert is_valid_title("(empty response)[Skill result: memory_search]") is False
    assert is_valid_title('{"success":true,"data":{}}') is False
    assert is_valid_title("Hi") is False
    assert is_valid_title("Title\nWith Newline") is False


def test_clean_title_string():
    assert clean_title_string(' "1. Top 10 Facts About AI" ') == "Top 10 Facts About AI"
    assert clean_title_string("- High Retention Title\n") == "High Retention Title"


def test_parse_titles_formats():
    ts = TitleStage()
    # Test JSON list of objects format
    json_objects = '[{"title": "The Secret Life of Ancient Rome"}, {"title": "Why Ancient Rome Really Fell"}]'
    titles_obj = ts._parse_titles(json_objects)
    assert len(titles_obj) == 2
    assert "The Secret Life of Ancient Rome" in titles_obj
    assert "Why Ancient Rome Really Fell" in titles_obj

    # Test JSON list of strings format
    json_strings = '["The Secret Life of Ancient Rome", "Why Ancient Rome Really Fell"]'
    titles_str = ts._parse_titles(json_strings)
    assert len(titles_str) == 2
    assert "The Secret Life of Ancient Rome" in titles_str

    # Test JSON dict format
    json_dict = '{"titles": ["The Secret Life of Ancient Rome", "Why Ancient Rome Really Fell"]}'
    titles_dict = ts._parse_titles(json_dict)
    assert len(titles_dict) == 2
    assert "The Secret Life of Ancient Rome" in titles_dict


@pytest.mark.asyncio
async def test_duplicate_filter_disk_and_memory(tmp_path):
    from app.pipeline.duplicate_checker import DuplicateFilter
    dup_filter = DuplicateFilter(base_output_dir=str(tmp_path))

    title = "Uncovering The Lost Artifacts"
    assert await dup_filter.is_duplicate(title) is False

    dup_filter.record(title)
    assert await dup_filter.is_duplicate(title) is True
    assert await dup_filter.is_duplicate("uncovering the lost artifacts") is True

    # Test disk duplicate detection
    disk_title = "Building The Future Of AI"
    folder_name = "building_the_future_of_ai"
    (tmp_path / folder_name).mkdir(parents=True, exist_ok=True)

    assert await dup_filter.is_duplicate(disk_title) is True



