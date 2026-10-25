import json
import pytest
from unittest.mock import AsyncMock
from app.models.preset import ContentPreset
from app.utils.srt_parser import SRTChunk
from app.pipeline.stages.scene_stage import SceneStage
from app.pipeline.stages.image_prompt_stage import ImagePromptStage
from app.models.generation import VisualContinuityState, ScenePrompt


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


@pytest.mark.asyncio
async def test_image_prompt_stage_concurrent_batch_generation(mock_preset):
    """Verify that ImagePromptStage batches scenes for projects with > 3 scenes and generates them concurrently."""
    import json
    batch_calls = []

    mock_ai = AsyncMock(spec=AnthropicClient)

    async def mock_generate_message(messages, system=None):
        content = messages[0]["content"]
        if "recurring_characters" in content:
            return {
                "text": '{"recurring_characters": {}, "recurring_locations": {}, "art_style_anchor": "Blueprint schematic style"}'
            }
        else:
            batch_calls.append(content)
            # Find which scenes were requested in this batch
            import re
            beat_nums = [int(m) for m in re.findall(r'Beat (\d+)', content)]
            batch_resp = [
                {
                    "scene_number": num,
                    "scene_index": num - 1,
                    "visual_description": f"Visual for scene {num}",
                    "characters_present": [],
                    "location": "HQ",
                    "mood_lighting": "Dynamic",
                    "camera_angle": "Wide",
                    "detailed_image_prompt": f"Detailed prompt for scene {num}, Blueprint schematic style"
                }
                for num in set(beat_nums)
            ]
            return {"text": json.dumps(batch_resp)}

    mock_ai.generate_message.side_effect = mock_generate_message

    stage = ImagePromptStage(ai_client=mock_ai, batch_size=5, max_concurrency=2)

    # 10 scenes
    scenes = [
        {"scene_number": i + 1, "narration_segment": f"Narration {i + 1}", "start_time": f"00:00:0{i},000", "end_time": f"00:00:0{i+1},000"}
        for i in range(10)
    ]

    prompts, continuity = await stage.process(scenes, mock_preset, topic="Big Scale Video")

    assert len(prompts) == 10
    # Should have split 10 scenes into 2 batches of 5
    assert len(batch_calls) == 2
    for idx, p in enumerate(prompts, start=1):
        assert p.scene_number == idx
        assert f"scene {idx}" in p.detailed_image_prompt.lower()
        assert "Blueprint schematic style" in p.detailed_image_prompt


def test_sentence_context_reconstruction_across_srt_chunks():
    """Verify that SceneStage reconstructs complete sentence boundaries across multiple fragmented SRT chunks."""
    stage = SceneStage()
    chunks = [
        SRTChunk(index=1, start_time="00:00:00,000", end_time="00:00:01,500", text="On December first, 1951,"),
        SRTChunk(index=2, start_time="00:00:01,500", end_time="00:00:03,000", text="a violent Pacific gale slammed into San Francisco"),
        SRTChunk(index=3, start_time="00:00:03,000", end_time="00:00:04,500", text="with sustained winds screaming past sixty-nine miles per hour."),
        SRTChunk(index=4, start_time="00:00:04,500", end_time="00:00:06,000", text="Out over the boiling waters,"),
        SRTChunk(index=5, start_time="00:00:06,000", end_time="00:00:08,000", text="the suspension bridge began to roll."),
    ]

    scenes = stage._build_scenes_from_srt_chunks(chunks)
    assert len(scenes) == 5

    # Chunks 1, 2, 3 belong to the same sentence
    sentence_1 = "On December first, 1951, a violent Pacific gale slammed into San Francisco with sustained winds screaming past sixty-nine miles per hour."
    assert scenes[0]["full_sentence"] == sentence_1
    assert scenes[1]["full_sentence"] == sentence_1
    assert scenes[2]["full_sentence"] == sentence_1

    # Chunks 4, 5 belong to the second sentence
    sentence_2 = "Out over the boiling waters, the suspension bridge began to roll."
    assert scenes[3]["full_sentence"] == sentence_2
    assert scenes[4]["full_sentence"] == sentence_2


def test_style_anchor_deduplication():
    """Verify that attach_style_anchor idempotently attaches anchors without duplicate repeating strings."""
    from app.pipeline.stages.image_prompt_stage import attach_style_anchor

    anchor = "Cinematic documentary photography, shot on 35mm film, authentic grain, dramatic lighting"
    base_prompt = "A massive concrete pier holding firm against churning ocean swells"

    # 1. Base attach
    res1 = attach_style_anchor(base_prompt, anchor)
    assert res1 == f"{base_prompt}, {anchor}"

    # 2. Idempotent re-attach (must not duplicate)
    res2 = attach_style_anchor(res1, anchor)
    assert res2 == res1
    assert res2.count("Cinematic documentary photography") == 1
    assert res2.count("dramatic lighting") == 1

    # 3. Partial sub-phrase at end stripped before canonical re-attach
    stutter_prompt = f"{base_prompt}, authentic grain, dramatic lighting"
    res3 = attach_style_anchor(stutter_prompt, anchor)
    assert res3 == f"{base_prompt}, {anchor}"
    assert res3.count("dramatic lighting") == 1


@pytest.mark.asyncio
async def test_critic_refinement_of_metaphorical_literalism(mock_preset):
    """Verify that the Critic detects off-concept literalism and replaces it with grounded narrative prompt."""
    mock_ai = AsyncMock(spec=AnthropicClient)

    # Simulation: Generator generated literal playing cards for 'house of cards'
    async def mock_generate_message(messages, system=None):
        content = messages[0]["content"]
        if "recurring_characters" in content:
            return {"text": '{"recurring_characters": {}, "recurring_locations": {}, "art_style_anchor": "Blueprint schematic style"}'}
        elif "candidate_prompt" in content:
            # Critic call: detect off_concept literal playing cards
            return {
                "text": json.dumps({
                    "evaluations": [
                        {
                            "scene_number": 1,
                            "relevance_score": 45.0,
                            "is_off_concept": True,
                            "critique": "Literal playing cards rendered for corporate insolvency idiom",
                            "refined_prompt": "An empty trading floor desk covered in discarded audit spreadsheets and ringing red telephone terminals"
                        }
                    ]
                })
            }
        else:
            # Generator candidate
            return {
                "text": json.dumps({
                    "visual_description": "Literal playing cards",
                    "characters_present": [],
                    "location": "Casino",
                    "mood_lighting": "Dim",
                    "camera_angle": "Close up",
                    "detailed_image_prompt": "A flimsy house of cards collapsing on a green felt casino table"
                })
            }

    mock_ai.generate_message.side_effect = mock_generate_message

    stage = ImagePromptStage(ai_client=mock_ai, enable_critic=True, quality_threshold=80.0)

    scenes = [
        {
            "scene_number": 1,
            "narration_segment": "Their financial empire was an unstable house of cards.",
            "full_sentence": "Their financial empire was an unstable house of cards waiting for the slightest tremor.",
            "start_time": "00:00:00,000",
            "end_time": "00:00:03,000",
            "visual_description": "A house of cards collapsing"
        }
    ]

    # Force critic invocation by passing reviewer_rules
    mock_preset.reviewer_rules.require_continuity = True
    stage.enable_critic = True

    # Use explicit critic method directly to verify audit and refinement
    prompts = [
        ScenePrompt(
            scene_number=1,
            narration_segment=scenes[0]["narration_segment"],
            full_sentence=scenes[0]["full_sentence"],
            visual_description=scenes[0]["visual_description"],
            detailed_image_prompt="A flimsy house of cards collapsing on a green felt casino table"
        )
    ]
    continuity = VisualContinuityState(art_style_anchor="Blueprint schematic style")

    refined = await stage._critique_and_refine_prompts(prompts, scenes, continuity, mock_preset, "Corporate Collapse")

    assert len(refined) == 1
    assert refined[0].is_off_concept is True
    assert refined[0].relevance_score == 45.0
    assert "empty trading floor desk" in refined[0].detailed_image_prompt
    assert "playing cards" not in refined[0].detailed_image_prompt


def test_style_anchor_deduplication_sentence_prefix_and_punctuation():
    """Verify that attach_style_anchor handles sentence-level prefixes, clause overlaps, and punctuation without stutter."""
    from app.pipeline.stages.image_prompt_stage import attach_style_anchor

    anchor = "Cinematic documentary photography, shot on 35mm film, authentic grain, dramatic lighting."
    base_prompt = "A massive concrete pier holding firm against churning ocean swells"

    # 1. Overlapping sentence prefix at the end of prompt
    prompt_with_sentence_prefix = f"{base_prompt}. Cinematic documentary photography, shot on 35mm film"
    res1 = attach_style_anchor(prompt_with_sentence_prefix, anchor)
    assert res1 == f"{base_prompt}, {anchor.rstrip(' .')}"
    assert res1.count("Cinematic documentary photography") == 1

    # 2. Overlapping clause
    prompt_with_clause = f"{base_prompt}, authentic grain, dramatic lighting"
    res2 = attach_style_anchor(prompt_with_clause, anchor)
    assert res2 == f"{base_prompt}, {anchor.rstrip(' .')}"
    assert res2.count("dramatic lighting") == 1

    # 3. Trailing punctuation cleaned before attach
    prompt_with_period = f"{base_prompt}."
    res3 = attach_style_anchor(prompt_with_period, anchor)
    assert res3 == f"{base_prompt}, {anchor.rstrip(' .')}"
    assert ".," not in res3
    assert ",," not in res3


@pytest.mark.asyncio
async def test_hardened_prompt_writing_anti_surrealism_and_zero_text_instructions(mock_preset):
    """Verify that prompt generation strictly injects anti-surrealism, zero-text mandate, and reality anchor into LLM prompts."""
    captured_prompts = []
    mock_ai = AsyncMock(spec=AnthropicClient)

    async def mock_generate_message(messages, system=None):
        content = messages[0]["content"]
        captured_prompts.append(content)
        if "recurring_characters" in content:
            return {
                "text": json.dumps({
                    "recurring_characters": {},
                    "recurring_locations": {},
                    "art_style_anchor": "Blueprint schematic style",
                    "world_setting": "High-altitude suspension bridge engineering and marine storm conditions",
                    "thematic_motifs": ["steel cables", "concrete caissons", "anemometers"],
                    "forbidden_cliches": ["floating gears", "surreal cartoon bridges", "lightning monsters"]
                })
            }
        else:
            return {
                "text": json.dumps({
                    "visual_description": "Bridge tower resisting gale",
                    "characters_present": [],
                    "location": "Bridge caisson",
                    "mood_lighting": "Stormy daylight",
                    "camera_angle": "Low-angle hero view",
                    "detailed_image_prompt": "Low-angle shot of massive bridge tower anchor resisting storm waves"
                })
            }

    mock_ai.generate_message.side_effect = mock_generate_message
    stage = ImagePromptStage(ai_client=mock_ai)

    scenes = [
        {
            "scene_number": 1,
            "narration_segment": "the suspension bridge began to roll.",
            "full_sentence": "Out over the boiling waters, the suspension bridge began to roll under sustained 70mph winds.",
            "start_time": "00:00:00,000",
            "end_time": "00:00:03,000",
            "visual_description": "Bridge rolling in wind"
        }
    ]

    prompts, continuity = await stage.process(scenes, mock_preset, topic="Bridge Physics")

    # Verify continuity extracted world_setting and forbidden_cliches
    assert "High-altitude suspension bridge engineering" in continuity.world_setting
    assert "floating gears" in continuity.forbidden_cliches

    # Verify generator prompt contains all hardened constraints
    gen_call = [p for p in captured_prompts if "CURRENT BEAT" in p][0]
    assert "Authentic World Setting:" in gen_call
    assert "High-altitude suspension bridge engineering" in gen_call
    assert "Absolute Anti-Literalism & Zero-Surrealism:" in gen_call
    assert "NO body-horror or physical mutilation" in gen_call
    assert "Absolute Zero-Text Mandate:" in gen_call
    assert "NEVER request text, letters, words in quotes, typography" in gen_call
    assert "Full Sentence Context:" in gen_call


@pytest.mark.asyncio
async def test_critic_refinement_strips_anchor_leakage_and_fixes_surrealism(mock_preset):
    """Verify that Critic detects surreal body-horror/metaphors, cleans anchor leakage from refined prompts, and flags off_concept."""
    mock_ai = AsyncMock(spec=AnthropicClient)

    async def mock_generate_message(messages, system=None):
        content = messages[0]["content"]
        # Critic call
        return {
            "text": json.dumps({
                "evaluations": [
                    {
                        "scene_number": 1,
                        "relevance_score": 35.0,
                        "is_off_concept": True,
                        "critique": "Surrealist marionette puppet strings into tendons is unacceptable body horror for psychology video",
                        "refined_prompt": "Extreme macro close-up of bloodshot eyes staring at glowing smartphone in dark bedroom, Blueprint schematic style"
                    }
                ]
            })
        }

    mock_ai.generate_message.side_effect = mock_generate_message
    stage = ImagePromptStage(ai_client=mock_ai, enable_critic=True, quality_threshold=80.0)

    scenes = [
        {
            "scene_number": 1,
            "narration_segment": "by an invisible puppeteer wired directly into",
            "full_sentence": "Your fingers keep moving, as if operated by an invisible puppeteer wired directly into your nervous system.",
            "start_time": "00:00:00,000",
            "end_time": "00:00:03,000",
            "visual_description": "Marionette strings in skin"
        }
    ]

    prompts = [
        ScenePrompt(
            scene_number=1,
            narration_segment=scenes[0]["narration_segment"],
            full_sentence=scenes[0]["full_sentence"],
            visual_description=scenes[0]["visual_description"],
            detailed_image_prompt="Surreal bioluminescent marionette threads piercing into tendons of hand"
        )
    ]
    continuity = VisualContinuityState(art_style_anchor="Blueprint schematic style")

    refined = await stage._critique_and_refine_prompts(prompts, scenes, continuity, mock_preset, "Willpower and Dopamine")

    assert len(refined) == 1
    assert refined[0].is_off_concept is True
    assert refined[0].relevance_score == 35.0
    # Verify refined prompt replaced the surrealism
    assert "bloodshot eyes staring at glowing smartphone" in refined[0].detailed_image_prompt
    assert "marionette" not in refined[0].detailed_image_prompt
    # Verify anchor leakage was cleanly stripped inside _critique_and_refine_prompts
    assert not refined[0].detailed_image_prompt.endswith("Blueprint schematic style")



