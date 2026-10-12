import json
import re
from typing import Tuple, List

from app.ai.client import get_ai_client
from app.prompts.builder import PromptBuilder
from app.models.enums import StageLevel
from app.models.preset import ContentPreset as ContentPreset
from app.models.generation import ScenePrompt, VisualContinuityState

class ImagePromptStage:
    def __init__(self, ai_client=None, event_bus=None):
        self.ai = ai_client or get_ai_client()
        self.event_bus = event_bus
        self.prompt_builder = PromptBuilder()

    async def process(self, scenes: List[dict], preset: ContentPreset, topic: str) -> Tuple[List[ScenePrompt], VisualContinuityState]:
        """
        Extracts/builds VisualContinuityState (character descriptions, environment styles).
        Generates detailed cinematic prompts for each scene beat preserving visual continuity.
        Runs Image Prompt Critic and refines if needed.
        """
        # 1. Establish Continuity
        continuity = await self._build_continuity(scenes, preset, topic)

        # 2. Generate and Critique Prompts
        prompts = []
        for scene in scenes:
            scene_prompt = await self._generate_scene_prompt(scene, continuity, preset)

            # Simple critique logic: verify style anchor is in prompt
            if continuity.art_style_anchor.lower() not in scene_prompt.detailed_image_prompt.lower():
                 scene_prompt.detailed_image_prompt += f", {continuity.art_style_anchor}"

            prompts.append(scene_prompt)

        return prompts, continuity

    async def _build_continuity(self, scenes: List[dict], preset: ContentPreset, topic: str) -> VisualContinuityState:
        scene_text = "\n".join([f"Scene {s.get('scene_number', i)}: {s.get('visual_description', '')}" for i, s in enumerate(scenes)])

        prompt = self.prompt_builder.build(
            level=StageLevel.IMAGE_PROMPT,
            preset=preset,
            inputs={"topic": topic, "scenes": scene_text}
        )

        prompt += "\nOutput strictly as a JSON object with keys: 'recurring_characters' (dict mapping name to description), 'recurring_locations' (dict mapping name to description), and 'art_style_anchor' (string)."

        for _ in range(3):
            if hasattr(self.ai, "generate"):
                response = await self.ai.generate(prompt=prompt, role="generator")
                text = response.text
            else:
                response = await self.ai.generate_message(
                    messages=[{"role": "user", "content": prompt}],
                    system="You are an expert visual prompt engineer.\nCRITICAL INSTRUCTION: DO NOT USE ANY TOOLS OR SKILLS (e.g. memory_search).",
                )
                text = response["text"]

            try:
                # strip possible markdown wrapping
                text_clean = re.sub(r'^```json\s*', '', text.strip())
                text_clean = re.sub(r'\s*```$', '', text_clean)

                if "skill_result" in text_clean or "memory_search" in text_clean or "[Skill result:" in text_clean:
                    continue

                data = json.loads(text_clean)

                return VisualContinuityState(
                    recurring_characters=data.get("recurring_characters", {}),
                    recurring_locations=data.get("recurring_locations", {}),
                    art_style_anchor=data.get("art_style_anchor", "")
                )
            except Exception:
                pass

        return VisualContinuityState()

    async def _generate_scene_prompt(self, scene: dict, continuity: VisualContinuityState, preset: ContentPreset) -> ScenePrompt:
        # Construct prompt asking for ScenePrompt JSON schema
        prompt = f"""
        Design an image prompt for a single scene based on this context.

        Narration: {scene.get('narration_segment')}
        Timestamps: {scene.get('start_time', '')} to {scene.get('end_time', '')}
        Visual idea: {scene.get('visual_description')}
        Style anchor: {continuity.art_style_anchor}
        Known characters: {json.dumps(continuity.recurring_characters)}
        Known locations: {json.dumps(continuity.recurring_locations)}

        Return ONLY valid JSON matching this schema:
        {{
            "visual_description": "String",
            "characters_present": ["List of strings"],
            "location": "String",
            "mood_lighting": "String",
            "camera_angle": "String",
            "detailed_image_prompt": "String exactly ready to drop into an image generator"
        }}
        """

        for _ in range(3):
            if hasattr(self.ai, "generate"):
                response = await self.ai.generate(prompt=prompt, role="generator")
                text = response.text
            else:
                response = await self.ai.generate_message(
                    messages=[{"role": "user", "content": prompt}],
                    system="You are an expert cinematic image prompt creator.\nCRITICAL INSTRUCTION: DO NOT USE ANY TOOLS OR SKILLS (e.g. memory_search).",
                )
                text = response["text"]

            try:
                 text_clean = re.sub(r'^```json\s*', '', text.strip())
                 text_clean = re.sub(r'\s*```$', '', text_clean)

                 if "skill_result" in text_clean or "memory_search" in text_clean or "[Skill result:" in text_clean:
                     continue

                 data = json.loads(text_clean)

                 return ScenePrompt(
                     scene_number=scene.get("scene_number", 1),
                     narration_segment=scene.get("narration_segment", ""),
                     start_time=scene.get("start_time", ""),
                     end_time=scene.get("end_time", ""),
                     visual_description=data.get("visual_description", scene.get("visual_description", "")),
                     characters_present=data.get("characters_present", []),
                     location=data.get("location", ""),
                     mood_lighting=data.get("mood_lighting", ""),
                     camera_angle=data.get("camera_angle", ""),
                     detailed_image_prompt=data.get("detailed_image_prompt", "")
                 )
            except Exception:
                 pass

        # Fallback
        return ScenePrompt(
            scene_number=scene.get("scene_number", 1),
            narration_segment=scene.get("narration_segment", ""),
            start_time=scene.get("start_time", ""),
            end_time=scene.get("end_time", ""),
            visual_description=scene.get("visual_description", ""),
            detailed_image_prompt=f"{scene.get('visual_description', '')}, {continuity.art_style_anchor}"
        )
