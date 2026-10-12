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

logger = logging.getLogger(__name__)


def _time_str_to_seconds(t_str: str) -> float:
    """Converts HH:MM:SS,mmm or HH:MM:SS.mmm to seconds float."""
    if not t_str:
        return 0.0
    try:
        parts = t_str.replace(",", ".").split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except Exception:
        return 0.0


def _seconds_to_time_str(secs: float) -> str:
    """Converts seconds float to HH:MM:SS,mmm format."""
    secs = max(0.0, secs)
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    ms = int(round((secs - int(secs)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class SceneStage:
    def __init__(self, ai_client=None, event_bus=None):
        self.ai = ai_client or get_ai_client()
        self.event_bus = event_bus
        self.prompt_builder = PromptBuilder()

    async def process(self, script_or_chunks, preset: ContentPreset) -> List[dict]:
        """
        Breaks down a script into scenes matching the ScenePrompt schema.
        When SRT chunks are provided, guarantees a 2-3 second visual interval
        aligning with every subtitle chunk (merging sub-second fragments < 1.5s).
        """
        # 1. When SRT chunks with timestamps are provided:
        if isinstance(script_or_chunks, list) and len(script_or_chunks) > 0 and getattr(script_or_chunks[0], "index", None) is not None:
            srt_chunks = script_or_chunks
            scenes = self._build_scenes_from_srt_chunks(srt_chunks)
            if scenes:
                logger.info(f"Generated {len(scenes)} scenes directly aligned with SRT chunks (2-3s interval).")
                return scenes

        # 2. Fallback when raw text only is passed:
        script_text = script_or_chunks if isinstance(script_or_chunks, str) else str(script_or_chunks)
        return await self._process_text_breakdown(script_text, preset)

    def _build_scenes_from_srt_chunks(self, srt_chunks: List[SRTChunk], min_chunk_duration: float = 1.5) -> List[dict]:
        """
        Creates fine-grained scene beats targeting the 2-3 second image interval.
        Every subtitle chunk becomes its own scene, merging tiny sub-second chunks
        only if their duration is less than min_chunk_duration.
        """
        scenes = []
        cur_text_parts = []
        cur_start_str = ""
        cur_end_str = ""
        cur_start_sec = 0.0
        cur_end_sec = 0.0

        for chunk in srt_chunks:
            start_sec = _time_str_to_seconds(chunk.start_time)
            end_sec = _time_str_to_seconds(chunk.end_time)
            text = chunk.text.strip()
            if not text:
                continue

            if not cur_text_parts:
                cur_text_parts = [text]
                cur_start_str = chunk.start_time
                cur_end_str = chunk.end_time
                cur_start_sec = start_sec
                cur_end_sec = end_sec
            else:
                chunk_dur = cur_end_sec - cur_start_sec
                # If current accumulated duration is less than 1.5s, merge with next
                if chunk_dur < min_chunk_duration:
                    cur_text_parts.append(text)
                    cur_end_str = chunk.end_time
                    cur_end_sec = end_sec
                else:
                    # Finalize current scene beat
                    scenes.append({
                        "scene_number": len(scenes) + 1,
                        "narration_segment": " ".join(cur_text_parts),
                        "start_time": cur_start_str,
                        "end_time": cur_end_str,
                        "visual_description": " ".join(cur_text_parts),
                    })
                    cur_text_parts = [text]
                    cur_start_str = chunk.start_time
                    cur_end_str = chunk.end_time
                    cur_start_sec = start_sec
                    cur_end_sec = end_sec

        if cur_text_parts:
            scenes.append({
                "scene_number": len(scenes) + 1,
                "narration_segment": " ".join(cur_text_parts),
                "start_time": cur_start_str,
                "end_time": cur_end_str,
                "visual_description": " ".join(cur_text_parts),
            })

        return scenes

    async def _process_text_breakdown(self, script_text: str, preset: ContentPreset) -> List[dict]:
        """Fallback LLM scene breakdown when no SRT is provided."""
        prompt = self.prompt_builder.build(
            level=StageLevel.SCENE_BREAKDOWN,
            preset=preset,
            inputs={"topic": preset.name, "script": script_text, "srt_chunks_xml": ""}
        )
        prompt += "\nOutput strict JSON: {'scenes': [{'scene_number': 1, 'narration_segment': '...', 'start_time': '00:00:00,000', 'end_time': '00:00:00,000', 'visual_description': '...'}, ...]}"

        for _ in range(3):
            if hasattr(self.ai, "generate"):
                response = await self.ai.generate(prompt=prompt, role="generator")
                text = response.text
            else:
                response = await self.ai.generate_message(
                    messages=[{"role": "user", "content": prompt}],
                    system="You are a scene planner breaking scripts into visual beats. Output valid JSON.\nCRITICAL INSTRUCTION: DO NOT USE ANY TOOLS OR SKILLS (e.g. memory_search).",
                )
                text = response["text"]

            try:
                text_clean = re.sub(r"^```json\s*", "", text.strip())
                text_clean = re.sub(r"\s*```$", "", text_clean)

                if "skill_result" in text_clean or "memory_search" in text_clean or "[Skill result:" in text_clean:
                    continue

                data = json.loads(text_clean)
                if "scenes" in data:
                    return data["scenes"]
                if isinstance(data, list) and len(data) > 0:
                    return data
                return [data] if isinstance(data, dict) else data
            except Exception:
                pass

        return [{
            "scene_number": 1,
            "narration_segment": script_text,
            "start_time": "00:00:00,000",
            "end_time": "00:00:00,000",
            "visual_description": "Full scene"
        }]
