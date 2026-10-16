import asyncio
import inspect
import re
from typing import Optional, List

from app.models.preset import ContentPreset
from app.models.generation import GenerationPackage, ScenePrompt

from app.pipeline.stages.title_stage import TitleStage
from app.pipeline.duplicate_checker import DuplicateFilter
from app.pipeline.stages.script_stage import ScriptStage
from app.pipeline.stages.scene_stage import SceneStage
from app.pipeline.stages.image_prompt_stage import ImagePromptStage
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
                 image_prompt_stage=None, final_review_stage=None,
                 db_coordinator=None, base_output_dir=None):
        self.duplicate_filter = DuplicateFilter(db_coordinator=db_coordinator, base_output_dir=base_output_dir)
        self.title_stage = title_stage or TitleStage(duplicate_filter=self.duplicate_filter, base_output_dir=base_output_dir)
        self.script_stage = script_stage or ScriptStage()
        self.scene_stage = scene_stage or SceneStage()
        self.image_prompt_stage = image_prompt_stage or ImagePromptStage()
        self.final_review_stage = final_review_stage or FinalReviewStage()
        self.base_output_dir = base_output_dir

    async def run(self, topic: str, preset: ContentPreset, generate_prompts: bool = False, audio_chunks: Optional[List[str]] = None, custom_output_dir: Optional[str] = None) -> GenerationPackage:
        """
        Orchestrates pipeline stages according to the modular decoupled contract:
        - Phase 1 (Script & Title generation): Generates Title, Script, and Metadata.
        - Phase 2 (Audio-synchronized image prompts): Once TTS finishes and transcribed chunks are available (or requested),
          it breaks down scenes and generates style-locked image prompts matching audio chunks.
        """
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
        effective_output_dir = custom_output_dir or self.base_output_dir or (preset.output_dir if hasattr(preset, 'output_dir') else None)
        best_title, tags, description = await self.title_stage.process(topic, preset)
        package.title = best_title
        package.seo_tags = tags
        package.seo_description = description
        package.normalized_title = slugify_title(package.title, topic=topic)

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

        # 5. Generate 3 distinct thumbnail prompts using the preset's built-in thumbnail styles
        package.thumbnail_prompts = await self.generate_thumbnail_prompts(package, preset)

        # 6. Final Review
        package = await self.final_review_stage.process(package)

        return package

    async def generate_thumbnail_prompts(self, package: GenerationPackage, preset: ContentPreset) -> List[str]:
        """
        Generates 3 distinct YouTube thumbnail prompts based on the preset's 3 built-in thumbnail styles.
        """
        from app.storage.exporter import ContentExporter
        from app.prompts.builder import PromptBuilder
        import json, re

        default_data = ContentExporter._get_or_generate_thumbnail_prompts(package, preset)
        fallback_prompts = [item["prompt"] for item in default_data]

        ai_client = getattr(self.image_prompt_stage, "ai", None)
        if not ai_client:
            return fallback_prompts

        try:
            anchor = package.continuity.art_style_anchor or getattr(preset.image_rules, "visual_style", "")
            payload = PromptBuilder.build_thumbnail_prompts_messages(
                topic=package.topic,
                title=package.title,
                preset=preset,
                art_style_anchor=anchor
            )
            prompt_content = payload["messages"][0]["content"]
            system_prompt = payload.get("system", "")

            if hasattr(ai_client, "generate"):
                res = ai_client.generate(prompt=prompt_content, role="generator")
                response = await res if inspect.isawaitable(res) else res
                if hasattr(response, "text") and isinstance(response.text, str):
                    raw_text = response.text.strip()
                elif isinstance(response, str):
                    raw_text = response.strip()
                else:
                    raw_text = ""
            elif hasattr(ai_client, "generate_message"):
                res = ai_client.generate_message(
                    messages=[{"role": "user", "content": prompt_content}],
                    system=system_prompt
                )
                response = await res if inspect.isawaitable(res) else res
                if isinstance(response, dict) and isinstance(response.get("text"), str):
                    raw_text = response["text"].strip()
                elif isinstance(response, str):
                    raw_text = response.strip()
                else:
                    raw_text = ""
            else:
                return fallback_prompts

            from app.prompts.parser import extract_json
            parsed = extract_json(raw_text)
            if isinstance(parsed, dict):
                for k in ["thumbnail_prompts", "thumbnails", "prompts", "candidates"]:
                    if isinstance(parsed.get(k), list):
                        parsed = parsed[k]
                        break

            if isinstance(parsed, list) and len(parsed) >= 1:
                llm_prompts = []
                for idx, item in enumerate(parsed[:3]):
                    if isinstance(item, dict):
                        p_text = item.get("thumbnail_prompt") or item.get("prompt") or item.get("text") or ""
                    elif isinstance(item, str):
                        p_text = item
                    else:
                        p_text = ""

                    if p_text and p_text.strip():
                        llm_prompts.append(p_text.strip())
                    elif idx < len(fallback_prompts):
                        llm_prompts.append(fallback_prompts[idx])

                while len(llm_prompts) < 3 and len(llm_prompts) < len(fallback_prompts):
                    llm_prompts.append(fallback_prompts[len(llm_prompts)])

                if len(llm_prompts) == 3:
                    return llm_prompts
        except Exception:
            pass

        return fallback_prompts

