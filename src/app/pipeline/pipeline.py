from typing import Optional, List

from app.models.preset import ContentPreset
from app.models.generation import GenerationPackage, ScenePrompt

from app.pipeline.stages.title_stage import TitleStage, DuplicateFilter
from app.pipeline.stages.script_stage import ScriptStage
from app.pipeline.stages.scene_stage import SceneStage
from app.pipeline.stages.image_prompt_stage import ImagePromptStage
from app.pipeline.stages.final_review_stage import FinalReviewStage


class GenerationPipeline:
    def __init__(self, title_stage=None, script_stage=None, scene_stage=None,
                 image_prompt_stage=None, final_review_stage=None):
        self.duplicate_filter = DuplicateFilter()
        self.title_stage = title_stage or TitleStage(self.duplicate_filter)
        self.script_stage = script_stage or ScriptStage()
        self.scene_stage = scene_stage or SceneStage()
        self.image_prompt_stage = image_prompt_stage or ImagePromptStage()
        self.final_review_stage = final_review_stage or FinalReviewStage()

    async def run(self, topic: str, preset: ContentPreset, generate_prompts: bool = False, audio_chunks: Optional[List[str]] = None) -> GenerationPackage:
        """
        Orchestrates pipeline stages according to the modular decoupled contract:
        - Phase 1 (Script & Title generation): Generates Title, Script, and Metadata.
        - Phase 2 (Audio-synchronized image prompts): Once TTS finishes and transcribed chunks are available (or requested),
          it breaks down scenes and generates style-locked image prompts matching audio chunks.
        """
        package = GenerationPackage(
            topic=topic,
            preset_name=preset.name,
            voice_name=preset.voice_name if hasattr(preset, 'voice_name') else "en_us_male_dry_narrator",
            title="",
            normalized_title="",
            script="",
            prompts=[]
        )

        # 1. Title Generation
        package.title = await self.title_stage.process(topic, preset)
        package.normalized_title = package.title.lower().replace(" ", "_").replace(":", "")

        # 2. Script Generation
        package.script = await self.script_stage.process(topic, package.title, preset)
        words = len(package.script.split())
        package.total_words = words
        package.estimated_duration_sec = words / 2.5 # ~150 words per min = 2.5 words per sec

        # 3. If image prompts are explicitly requested or audio chunks provided:
        if generate_prompts or audio_chunks:
            source_content = "\n\n".join(audio_chunks) if audio_chunks else package.script
            scenes_data = await self.scene_stage.process(source_content, preset)

            # 4. Image Prompt & Continuity Generation
            prompts, continuity = await self.image_prompt_stage.process(scenes_data, preset, topic)
            package.prompts = prompts
            package.continuity = continuity

        # 5. Final Review
        package = await self.final_review_stage.process(package)

        return package
