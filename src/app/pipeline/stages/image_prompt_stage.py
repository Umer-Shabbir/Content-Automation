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
        total_scenes = len(scenes)
        for i, scene in enumerate(scenes):
            prev_narration = scenes[i - 1].get("narration_segment", "") if i > 0 else "None (Beginning of video)"
            next_narration = scenes[i + 1].get("narration_segment", "") if i + 1 < total_scenes else "None (End of video)"
            scene_prompt = await self._generate_scene_prompt(
                scene=scene,
                continuity=continuity,
                preset=preset,
                topic=topic,
                scene_index=i + 1,
                total_scenes=total_scenes,
                prev_narration=prev_narration,
                next_narration=next_narration,
            )

            # Critique logic: verify style anchor is in prompt
            if continuity.art_style_anchor and continuity.art_style_anchor.lower() not in scene_prompt.detailed_image_prompt.lower():
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

    async def _generate_scene_prompt(
        self,
        scene: dict,
        continuity: VisualContinuityState,
        preset: ContentPreset,
        topic: str = "",
        scene_index: int = 1,
        total_scenes: int = 1,
        prev_narration: str = "",
        next_narration: str = "",
    ) -> ScenePrompt:
        preset_style_desc = getattr(preset, "visual_style", "") or continuity.art_style_anchor
        narration = scene.get("narration_segment", "")

        prompt = f"""You are an expert cinematic image prompt engineer crafting visual prompts for an automated video generator.
Produce a stunning, detailed, cinematic image prompt for Scene Beat {scene_index} of {total_scenes}.

Even if the current narration beat is concise, use the surrounding narrative flow and story arc to depict this exact moment vividly and consistently.

Video Topic: {topic or 'Cinematic Video'}
Art Style Anchor: {continuity.art_style_anchor}
Preset Visual Guidelines: {preset_style_desc}

Narrative Flow:
- Preceding Beat: "{prev_narration}"
- CURRENT BEAT (Beat {scene_index}): "{narration}"
- Upcoming Beat: "{next_narration}"

Timestamps: {scene.get('start_time', '')} to {scene.get('end_time', '')}
Visual Idea: {scene.get('visual_description', narration)}
Known Characters: {json.dumps(continuity.recurring_characters)}
Known Locations: {json.dumps(continuity.recurring_locations)}

Requirements:
1. Depict the CURRENT BEAT with concrete visual actions, specific subject matter, environment depth, and composition.
2. Define a dramatic camera angle (e.g., dynamic close-up, low-angle hero shot, wide panoramic view).
3. Specify atmospheric mood lighting (e.g., volumetric god rays, deep chiaroscuro, soft diffused ambient light).
4. The 'detailed_image_prompt' must be complete and ready for an image generation model (Imagen 3, FLUX, Midjourney), ending with the visual style anchor.

Return ONLY valid JSON matching this schema:
{{
    "visual_description": "Clear description of the visual scene",
    "characters_present": ["List of character names present or empty list"],
    "location": "Setting/environment description",
    "mood_lighting": "Specific mood and lighting atmosphere",
    "camera_angle": "Camera framing and perspective",
    "detailed_image_prompt": "Highly detailed, descriptive image generation prompt ending with the style anchor"
}}"""

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
                    scene_number=scene.get("scene_number", scene_index),
                    narration_segment=narration,
                    start_time=scene.get("start_time", ""),
                    end_time=scene.get("end_time", ""),
                    visual_description=data.get("visual_description", scene.get("visual_description", narration)),
                    characters_present=data.get("characters_present", []),
                    location=data.get("location", ""),
                    mood_lighting=data.get("mood_lighting", ""),
                    camera_angle=data.get("camera_angle", ""),
                    detailed_image_prompt=data.get("detailed_image_prompt", "")
                )
            except Exception:
                pass

        # Fallback with enriched detail
        fallback_prompt = f"Cinematic shot of {scene.get('visual_description', narration)}, {continuity.art_style_anchor or preset_style_desc}"
        return ScenePrompt(
            scene_number=scene.get("scene_number", scene_index),
            narration_segment=narration,
            start_time=scene.get("start_time", ""),
            end_time=scene.get("end_time", ""),
            visual_description=scene.get("visual_description", narration),
            detailed_image_prompt=fallback_prompt
        )
