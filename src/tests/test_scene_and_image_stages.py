import pytest
from unittest.mock import AsyncMock
from app.models.preset import ContentPreset
from app.utils.srt_parser import SRTChunk
from app.pipeline.stages.scene_stage import SceneStage
from app.pipeline.stages.image_prompt_stage import ImagePromptStage
from app.models.generation import VisualContinuityState


from app.ai.client import AnthropicClient


@pytest.fixture
def mock_preset():
    return ContentPreset(name="blueprint", output_dir="test_output", visual_style="Blueprint architectural schematic")


def test_scene_stage_1_to_1_mapping_without_merging(mock_preset):
    """Verify that SceneStage creates strictly 1 scene beat per SRT chunk without merging short chunks."""
    stage = SceneStage()
    # 5 chunks with various durations including sub-second (< 1.5s) durations
    chunks = [
        SRTChunk(index=1, start_time="00:00:00,000", end_time="00:00:00,800", text="Welcome back."),
        SRTChunk(index=2, start_time="00:00:00,800", end_time="00:00:01,200", text="To the show."),
        SRTChunk(index=3, start_time="00:00:01,200", end_time="00:00:03,500", text="Today we uncover the truth."),
        SRTChunk(index=4, start_time="00:00:03,500", end_time="00:00:04,100", text="Look here."),
        SRTChunk(index=5, start_time="00:00:04,100", end_time="00:00:07,000", text="Everything changes now."),
    ]

    scenes = stage._build_scenes_from_srt_chunks(chunks)
    assert len(scenes) == 5, f"Expected 5 scenes, got {len(scenes)} (chunks were inappropriately merged!)"

    for i, scene in enumerate(scenes, start=1):
        assert scene["scene_number"] == i
        assert scene["narration_segment"] == chunks[i - 1].text
        assert scene["start_time"] == chunks[i - 1].start_time
        assert scene["end_time"] == chunks[i - 1].end_time


@pytest.mark.asyncio
async def test_image_prompt_stage_context_enrichment(mock_preset):
    """Verify that ImagePromptStage enriches the prompt with previous beat, current beat, next beat, topic, and continuity."""
    captured_prompts = []

    mock_ai = AsyncMock(spec=AnthropicClient)

    async def mock_generate_message(messages, system=None):
        content = messages[0]["content"]
        captured_prompts.append(content)
        if "recurring_characters" in content:
            return {
                "text": '{"recurring_characters": {"Dr. Fox": "Brilliant scientist"}, "recurring_locations": {"Neo Lab": "Futuristic lab"}, "art_style_anchor": "Blueprint schematic style"}'
            }
        else:
            return {
                "text": '{"visual_description": "Detailed view", "characters_present": ["Dr. Fox"], "location": "Neo Lab", "mood_lighting": "Cyan glow", "camera_angle": "Close up", "detailed_image_prompt": "Cinematic blueprint of lab equipment, Blueprint schematic style"}'
            }

    mock_ai.generate_message.side_effect = mock_generate_message

    stage = ImagePromptStage(ai_client=mock_ai)

    scenes = [
        {"scene_number": 1, "narration_segment": "In the beginning there was chaos.", "start_time": "00:00:00,000", "end_time": "00:00:02,000"},
        {"scene_number": 2, "narration_segment": "Then Dr. Fox discovered the frequency.", "start_time": "00:00:02,000", "end_time": "00:00:04,500"},
        {"scene_number": 3, "narration_segment": "The machine whirred into action.", "start_time": "00:00:04,500", "end_time": "00:00:07,000"},
    ]

    topic = "The Quantum Breakthrough"
    prompts, continuity = await stage.process(scenes, mock_preset, topic=topic)

    assert len(prompts) == 3
    assert continuity.art_style_anchor == "Blueprint schematic style"

    # Find prompt generated for Scene 2 (the second scene prompt call)
    scene_2_call = [p for p in captured_prompts if "CURRENT BEAT (Beat 2)" in p]
    assert len(scene_2_call) == 1, "Did not find expected prompt call for Scene 2"
    prompt_text = scene_2_call[0]

    # Verify context enrichment in prompt
    assert "The Quantum Breakthrough" in prompt_text
    assert 'Preceding Beat: "In the beginning there was chaos."' in prompt_text
    assert 'CURRENT BEAT (Beat 2): "Then Dr. Fox discovered the frequency."' in prompt_text
    assert 'Upcoming Beat: "The machine whirred into action."' in prompt_text
    assert "Dr. Fox" in prompt_text
    assert "Neo Lab" in prompt_text
    assert "Blueprint architectural schematic" in prompt_text or "Blueprint schematic style" in prompt_text
