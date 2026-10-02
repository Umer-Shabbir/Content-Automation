import json
import logging
from typing import List, Dict, Any
import re

from app.ai.client import get_ai_client
from app.prompts.builder import PromptBuilder
from app.models.enums import StageLevel
from app.models.preset import ContentPreset
from app.models.generation import ScenePrompt
from app.utils.srt_parser import SRTChunk

class SceneStage:
    def __init__(self, ai_client=None, event_bus=None):
        self.ai = ai_client or get_ai_client()
        self.event_bus = event_bus
        self.prompt_builder = PromptBuilder()

    async def process(self, script_or_chunks, preset: ContentPreset) -> List[dict]:
        """
        Breaks down a script into scenes matching the ScenePrompt schema.
        Note: The actual transformation into ScenePrompt and detailed elements
        typically happens partially here and partially in ImagePromptStage!
        This function just parses what the LLM returns for a scene breakdown.
        """
        if isinstance(script_or_chunks, list) and len(script_or_chunks) > 0 and getattr(script_or_chunks[0], "index", None) is not None:
            srt_chunks = script_or_chunks
            srt_chunks_xml = "\n".join(chunk.to_xml() for chunk in srt_chunks)
            prompt = self.prompt_builder.build(
                level=StageLevel.SCENE_BREAKDOWN,
                preset=preset,
                inputs={"topic": preset.name, "srt_chunks_xml": srt_chunks_xml, "script": ""}
            )
            fallback_text = srt_chunks[0].text
        else:
            script_text = script_or_chunks
            prompt = self.prompt_builder.build(
                level=StageLevel.SCENE_BREAKDOWN,
                preset=preset,
                inputs={"topic": preset.name, "script": script_text, "srt_chunks_xml": ""} # fallback
            )
            fallback_text = script_text if isinstance(script_text, str) else str(script_text)

        prompt += "\nOutput strict JSON: {'scenes': [{'scene_number': 1, 'narration_segment': '...', 'start_time': '00:00:00,000', 'end_time': '00:00:00,000', 'visual_description': '...'}, ...]}"

        if hasattr(self.ai, "generate"):
            response = await self.ai.generate(prompt=prompt, role="generator")
            text = response.text
        else:
            response = await self.ai.generate_message(
                messages=[{"role": "user", "content": prompt}],
                system="You are a scene planner breaking scripts into visual beats. Output valid JSON.",
            )
            text = response["text"]

        try:
            text = re.sub(r"^```json\s*", "", text.strip())
            text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)

            if "scenes" in data:
                return data["scenes"]
            return [data] if isinstance(data, dict) else data
        except Exception:
            return [{"scene_number": 1, "narration_segment": fallback_text, "start_time": "00:00:00,000", "end_time": "00:00:00,000", "visual_description": "Full scene"}]
