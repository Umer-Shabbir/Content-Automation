import asyncio
import inspect
import re
from typing import Optional, List, Callable

from app.models.preset import ContentPreset
from app.models.generation import GenerationPackage, ScenePrompt

from app.pipeline.stages.title_stage import TitleStage
from app.pipeline.duplicate_checker import DuplicateFilter
from app.pipeline.stages.script_stage import ScriptStage
from app.pipeline.stages.scene_stage import SceneStage
from app.pipeline.stages.image_prompt_stage import ImagePromptStage
from app.pipeline.stages.thumbnail_stage import ThumbnailStage
from app.pipeline.stages.final_review_stage import FinalReviewStage


def slugify_title(title: str, topic: str = "") -> str:
    """
    Converts a title into a clean, filesystem-safe normalized slug.
    Replaces special characters and spaces with underscores.
    """
    if not title:
        title = topic or "untitled_project"

    # Lowercase
    slug = title.lower()
    # Filter out tool artifacts if present
    for kw in ["empty_response", "skill_result", "memory_search", "successtrue", "totaltokens"]:
        slug = slug.replace(kw, "")

    # Replace invalid chars and punctuation with spaces
    slug = re.sub(r'[^a-z0-9\s_-]', '', slug)
    # Replace whitespace and hyphens with underscores
    slug = re.sub(r'[\s-]+', '_', slug)
    # Collapse multiple underscores
    slug = re.sub(r'_+', '_', slug).strip('_')

    # Truncate length
    if len(slug) > 80:
        slug = slug[:80].rstrip('_')

    if not slug or len(slug) < 3:
        topic_slug = re.sub(r'[^a-z0-9]+', '_', topic.lower()).strip('_') if topic else "untitled"
        slug = f"project_{topic_slug}"[:80]

    return slug


class GenerationPipeline:
    def __init__(self, title_stage=None, script_stage=None, scene_stage=None,
                 image_prompt_stage=None, thumbnail_stage=None, final_review_stage=None,
                 db_coordinator=None, base_output_dir=None):
        self.duplicate_filter = DuplicateFilter(db_coordinator=db_coordinator, base_output_dir=base_output_dir)
        self.title_stage = title_stage or TitleStage(duplicate_filter=self.duplicate_filter, base_output_dir=base_output_dir)
        self.script_stage = script_stage or ScriptStage()
        self.scene_stage = scene_stage or SceneStage()
        self.image_prompt_stage = image_prompt_stage or ImagePromptStage()
        self.thumbnail_stage = thumbnail_stage or ThumbnailStage(ai_client=getattr(self.image_prompt_stage, "ai", None))
        self.final_review_stage = final_review_stage or FinalReviewStage()
        self.base_output_dir = base_output_dir

    def set_ai_client(self, ai_client):
        """Sets the AI client across all pipeline stages."""
        self.title_stage.ai = ai_client
        self.script_stage.ai = ai_client
        self.scene_stage.ai = ai_client
        self.image_prompt_stage.ai = ai_client
        self.thumbnail_stage.ai = ai_client
        self.final_review_stage.ai = ai_client

    async def run(self, topic: str, preset: ContentPreset, generate_prompts: bool = False, audio_chunks: Optional[List[str]] = None, custom_output_dir: Optional[str] = None, progress_callback: Optional[Callable[[str], None]] = None) -> GenerationPackage:
        """
        Orchestrates pipeline stages according to the modular decoupled contract:
        - Phase 1 (Script & Title generation): Generates Title, Script, and Metadata.
        - Phase 2 (Audio-synchronized image prompts): Once TTS finishes and transcribed chunks are available (or requested),
          it breaks down scenes and generates style-locked image prompts matching audio chunks.
        """
        # Synchronize thumbnail_stage and other stages if image_prompt_stage or script_stage has an active AI client
        active_ai = getattr(self.image_prompt_stage, "ai", None) or getattr(self.script_stage, "ai", None)
        if active_ai and getattr(self.thumbnail_stage, "ai", None) != active_ai:
            self.thumbnail_stage.ai = active_ai

        effective_output_dir = custom_output_dir or self.base_output_dir or preset.output_dir

        package = GenerationPackage(
            topic=topic,
            preset_name=preset.name,
            voice_name=preset.voice_name if hasattr(preset, 'voice_name') else "Adam   ·  American Male",
            video_language=preset.video_language if hasattr(preset, 'video_language') else "English",
            title="",
            normalized_title="",
            script="",
            prompts=[]
        )

        # 1. Title Generation
        if progress_callback:
            progress_callback("Generating title & fetching SEO context...")
        effective_output_dir = custom_output_dir or self.base_output_dir or (preset.output_dir if hasattr(preset, 'output_dir') else None)
        best_title, tags, description = await self.title_stage.process(topic, preset)
        package.title = best_title
        package.seo_tags = tags
        package.seo_description = description
        package.normalized_title = slugify_title(package.title, topic=topic)

        # 2. Script Generation
        if progress_callback:
            progress_callback(f"Generating script for '{best_title}'...")
        package.script = await self.script_stage.process(topic, package.title, preset)
        words = len(package.script.split())
        package.total_words = words
        package.estimated_duration_sec = words / 2.5 # ~150 words per min = 2.5 words per sec

        # 3. If image prompts are explicitly requested or audio chunks provided:
        if generate_prompts or audio_chunks:
            if progress_callback:
                progress_callback("Generating visual scene breakdowns & prompts...")
            source_content = "\n\n".join(audio_chunks) if audio_chunks else package.script
            scenes_data = await self.scene_stage.process(source_content, preset)

            # 4. Image Prompt & Continuity Generation
            prompts, continuity = await self.image_prompt_stage.process(scenes_data, preset, topic)
            package.prompts = prompts
            package.continuity = continuity

        # 5. Generate 3 distinct thumbnail prompts using the preset's built-in thumbnail styles
        if progress_callback:
            progress_callback("Generating thumbnail prompts (generator + critic)...")
        package.thumbnail_prompts = await self.generate_thumbnail_prompts(package, preset)

        # 6. Final Review
        if progress_callback:
            progress_callback("Running final quality review...")
        package = await self.final_review_stage.process(package)

        if progress_callback:
            progress_callback("Pipeline complete! Exporting files...")
        return package

    async def generate_thumbnail_prompts(self, package: GenerationPackage, preset: ContentPreset) -> List[str]:
        """
        Generates 3 distinct YouTube thumbnail prompts based on the preset's 3 built-in thumbnail styles
        using a two-step Generator + Critic pipeline.
        """
        return await self.thumbnail_stage.process(package, preset)

