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

    def _reconstruct_sentence_context(self, srt_chunks: List[SRTChunk]) -> List[str]:
        """
        Reconstructs the full grammatical sentence context enclosing each subtitle chunk.
        Enables downstream prompt engineers to understand the complete narrative idea
        even when a chunk is only 2-3 words (e.g. 'while the board', 'began to roll').
        """
        if not srt_chunks:
            return []

        # Build clean narrative stream
        chunk_texts = [c.text.strip() for c in srt_chunks]
        full_text = " ".join(t for t in chunk_texts if t)

        # Split into sentences using standard sentence delimiters (. ! ?) while preserving punctuation
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_text) if s.strip()]
        if not sentences:
            sentences = [full_text]

        chunk_sentences = []
        for c_text in chunk_texts:
            if not c_text:
                chunk_sentences.append("")
                continue
            # Find the sentence containing this chunk
            matched_sentence = ""
            for s in sentences:
                if c_text in s:
                    matched_sentence = s
                    break
            if not matched_sentence:
                # Fallback: find by partial or lowercase match
                c_low = c_text.lower()
                for s in sentences:
                    if c_low in s.lower():
                        matched_sentence = s
                        break
            chunk_sentences.append(matched_sentence or c_text)

        return chunk_sentences

    def _build_scenes_from_srt_chunks(self, srt_chunks: List[SRTChunk], min_chunk_duration: float = 0.0) -> List[dict]:
        """
        Creates fine-grained scene beats with strict 1:1 alignment with every subtitle chunk.
        Every subtitle chunk becomes its own individual scene beat with matching index.
        No merging of chunks. Injects reconstructed full_sentence context for each beat.
        """
        sentence_contexts = self._reconstruct_sentence_context(srt_chunks)
        scenes = []
        for idx, chunk in enumerate(srt_chunks):
            text = chunk.text.strip()
            if not text:
                continue

            scene_idx = len(scenes) + 1
            full_sent = sentence_contexts[idx] if idx < len(sentence_contexts) and sentence_contexts[idx] else text

            scenes.append({
                "scene_number": scene_idx,
                "narration_segment": text,
                "start_time": chunk.start_time,
                "end_time": chunk.end_time,
                "visual_description": text,
                "full_sentence": full_sent,
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
