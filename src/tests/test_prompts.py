import pytest
import json
from app.prompts.parser import extract_json, extract_tag_content, extract_script_text
from app.prompts.builder import PromptBuilder
from app.models.preset import TitleRules, ScriptRules, ImageRules, ReviewerRules, ContentPreset
from app.models.generation import GenerationPackage, VisualContinuityState, ScenePrompt

def test_extract_script_text_raw_narration():
    text = "They say time heals all wounds, but what does ten years do to a promise?"
    assert extract_script_text(text) == text

def test_extract_script_text_from_json_refined_script():
    json_text = json.dumps({
        "review": {"hook_strength": "Needs Improvement"},
        "decision": "REVISION REQUIRED",
        "refined_script": "They say time heals all wounds, but what does ten years do to a promise?"
    })
    extracted = extract_script_text(json_text)
    assert extracted == "They say time heals all wounds, but what does ten years do to a promise?"

def test_extract_script_text_from_json_review_metadata_only():
    json_text = json.dumps({
        "review": {"hook_strength": "Needs Improvement"},
        "decision": "REVISION REQUIRED",
        "recommendations": ["Make it shorter"]
    })
    fallback = "Original draft script text here."
    extracted = extract_script_text(json_text, fallback=fallback)
    assert extracted == fallback

def test_extract_script_text_markdown_wrapped():
    text = "```\nIn 1970, a legendary story was told.\n```"
    assert extract_script_text(text) == "In 1970, a legendary story was told."

def test_extract_script_text_xml_tagged():
    text = "<script>\nIn 1970, a legendary story was told.\n</script>"
    assert extract_script_text(text) == "In 1970, a legendary story was told."


def test_extract_json_markdown():
    text = "Here is the result:\n```json\n{\"title\": \"Test\"}\n```\nHope it helps!"
    result = extract_json(text)
    assert result == {"title": "Test"}

def test_extract_json_raw_object():
    text = "Some intro text { \"key\": \"value\", \"arr\": [1,2,3] } some outro"
    result = extract_json(text)
    assert result == {"key": "value", "arr": [1, 2, 3]}

def test_extract_json_raw_array():
    text = "Titles: \n [\n  {\"title\": \"A\"},\n  {\"title\": \"B\"}\n]\n"
    result = extract_json(text)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == {"title": "A"}

def test_extract_json_fallback_cleaning():
    # Test JSON with trailing comma which is invalid strict JSON
    text = "{ \"key\": \"value\", }"
    result = extract_json(text)
    assert result == {"key": "value"}

def test_extract_tag_content():
    text = "Some text <script>\nLine 1\nLine 2\n</script> More text"
    result = extract_tag_content(text, "script")
    assert result == "Line 1\nLine 2"

def test_extract_tag_content_not_found():
    text = "Just some text"
    result = extract_tag_content(text, "script")
    assert result is None

def test_builder_title_generation():
    rules = TitleRules(title_structure="Short", hook_style="Engaging", forbidden_patterns=["Test"])
    payload = PromptBuilder.build_title_generation_messages("Space", rules)

    assert "system" in payload
    assert "messages" in payload
    assert payload["messages"][0]["role"] == "user"
    assert "Space" in payload["messages"][0]["content"]
    assert "Short" in payload["messages"][0]["content"]

def test_builder_script_generation():
    rules = ScriptRules(target_words=500, strict_voiceover_only=True)
    payload = PromptBuilder.build_script_generation_messages(
        topic="Mars", title="Journey to Mars", rules=rules
    )

    assert "system" in payload
    assert len(payload["messages"]) == 1
    content = payload["messages"][0]["content"]
    assert "Mars" in content
    assert "YES! NO STAGE DIRECTIONS" in content

def test_builder_script_generation_with_feedback():
    rules = ScriptRules()
    payload = PromptBuilder.build_script_generation_messages(
        topic="Mars", title="Mars Base", rules=rules,
        feedback="Make it punchier", previous_draft="Old draft"
    )

    # User(initial), Assistant, User(feedback)
    assert len(payload["messages"]) == 3
    assert payload["messages"][1]["role"] == "assistant"
    assert payload["messages"][1]["content"] == "Old draft"
    assert payload["messages"][2]["role"] == "user"
    assert "Make it punchier" in payload["messages"][2]["content"]

def test_builder_scene_planning_with_srt():
    rules = ImageRules(visual_style="Dark", cinematic_style="Wide", scene_density="1 per 2")
    payload = PromptBuilder.build_scene_planning_messages("Space", "Title", "Script", rules, "<chunk>Hello</chunk>")

    assert "system" in payload
    assert len(payload["messages"]) == 1
    content = payload["messages"][0]["content"]
    assert "<chunk>Hello</chunk>" in content
    assert "Dark" in content

def test_builder_final_review():
    preset = ContentPreset(name="Test Preset")
    package = GenerationPackage(
        topic="Testing",
        preset_name="Test",
        title="Test Title",
        normalized_title="test-title",
        script="Hello world",
        prompts=[
            ScenePrompt(
                scene_number=1,
                narration_segment="Hello",
                visual_description="A man waving",
                detailed_image_prompt="A highly detailed image of a man waving"
            )
        ]
    )

    payload = PromptBuilder.build_final_review_messages(package, preset)
    assert "system" in payload
    assert len(payload["messages"]) == 1

    content = payload["messages"][0]["content"]
    # Check if package serialized
    assert "Test Title" in content
    assert "Hello world" in content
    # Check if preset serialized
    assert "Test Preset" in content

def test_sanitize_voiceover_script():
    from app.pipeline.stages.script_stage import sanitize_voiceover_script
    raw = (
        "[Music: Dramatic swelling]\n"
        "[Narrator]: In the heart of Wall Street, the bank was dying.\n"
        "(pause)\n"
        "No one could have predicted the collapse.\n"
        "[Sound effect: Sirens fading]"
    )
    cleaned = sanitize_voiceover_script(raw)
    assert "[Music" not in cleaned
    assert "[Narrator]" not in cleaned
    assert "(pause)" not in cleaned
    assert "[Sound effect" not in cleaned
    assert "In the heart of Wall Street" in cleaned
    assert "No one could have predicted the collapse." in cleaned

@pytest.mark.asyncio
async def test_script_stage_critic_feedback_loop():
    from unittest.mock import AsyncMock
    from app.pipeline.stages.script_stage import ScriptStage

    mock_ai = AsyncMock()
    # Attempt 0: generator returns draft with stage directions
    # Attempt 0: critic returns REVISE with feedback
    # Attempt 1: generator returns polished draft based on feedback
    # Attempt 1: critic returns APPROVE
    gen_call_1 = AsyncMock(text="[Narrator]: Bad throat-clearing intro. Today we explore finance. [Music]")
    critic_call_1 = AsyncMock(text='{"decision": "REVISE", "score": 65, "feedback": "Remove stage directions and use In Medias Res hook."}')
    gen_call_2 = AsyncMock(text="In the high-stakes world of finance, one phone call triggered the greatest market crash in human history.")
    critic_call_2 = AsyncMock(text='{"decision": "APPROVE", "score": 95, "feedback": "Outstanding retention hook."}')

    mock_ai.generate.side_effect = [gen_call_1, critic_call_1, gen_call_2, critic_call_2]

    stage = ScriptStage(ai_client=mock_ai)
    preset = ContentPreset(name="money_chuck")

    result = await stage.process("Market Crash", "The Day Wall Street Died", preset, retry_limit=3)
    assert "one phone call triggered" in result
    assert "[Narrator]" not in result
    assert "[Music]" not in result
    assert mock_ai.generate.call_count == 4
