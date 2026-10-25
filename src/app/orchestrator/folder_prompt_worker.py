import asyncio
import json
import logging
from pathlib import Path
from PySide6.QtCore import QThread, Signal

from app.models.api_profile import APIProfile, RequestConfig
from app.ai.client import AnthropicClient
from app.models.preset import BUILTIN_PRESETS, ContentPreset
from app.models.generation import GenerationPackage
from app.pipeline.stages.scene_stage import SceneStage
from app.pipeline.stages.image_prompt_stage import ImagePromptStage
from app.storage.exporter import ContentExporter

logger = logging.getLogger(__name__)


class FolderPromptWorker(QThread):
    """
    Asynchronously processes an existing project folder (which already has script.txt, audio.wav, project.json)
    and generates the style-locked scene image prompts (prompts.txt) for Round 2.
    """
    finished_signal = Signal(str, dict)  # folder_path, result_payload
    failed_signal = Signal(str, str)     # folder_path, error_message

    def __init__(self, folder_path: str, settings_data: dict, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.settings_data = settings_data

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_run())
        finally:
            loop.close()

    async def _async_run(self):
        folder = Path(self.folder_path)
        try:
            if not folder.exists():
                raise FileNotFoundError(f"Project folder not found: {self.folder_path}")

            script_file = folder / "script.txt"
            if not script_file.exists():
                raise FileNotFoundError(f"Missing script.txt in {folder.name}")

            script_text = script_file.read_text(encoding="utf-8").strip()
            if not script_text:
                raise ValueError("script.txt is empty.")

            # Check for optional parsed SRT (audio.srt or transcript.srt)
            srt_chunks = []
            srt_file = folder / "transcript.srt"
            if not srt_file.exists():
                srt_file = folder / "audio.srt"

            if srt_file.exists():
                from app.utils.srt_parser import SRTParser
                try:
                    srt_content = srt_file.read_text(encoding="utf-8")
                    srt_chunks = SRTParser.parse(srt_content)
                except Exception as e:
                    logger.warning(f"Failed to parse {srt_file.name}: {e}")

            # Read project.json for preset_name and topic
            preset_name = "money_chuck"
            topic = folder.name
            meta_file = folder / "project.json"
            if not meta_file.exists():
                meta_file = folder / "metadata.json"
            if meta_file.exists():
                try:
                    meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
                    preset_name = meta_data.get("preset_name", preset_name)
                    topic = meta_data.get("topic", topic)
                except Exception:
                    pass

            import copy
            base_preset = BUILTIN_PRESETS.get(preset_name, ContentPreset(name=preset_name))
            preset = copy.deepcopy(base_preset)

            # 1. Setup AI Client
            max_concurrent = self.settings_data.get("max_concurrent_requests", 3)
            request_config = RequestConfig(
                max_concurrent_requests=max_concurrent,
                request_timeout=180.0,
                max_tokens=8192
            )
            api_key_str = self.settings_data.get("api_key", "").strip() or "sk-dummy-key-for-local-testing"

            profile = APIProfile(
                name="prompt_worker_profile",
                base_url=self.settings_data.get("base_url", "https://api.anthropic.com"),
                api_key=api_key_str,
                model=self.settings_data.get("model", "claude-sonnet-4-6"),
                config=request_config
            )
            ai_client = AnthropicClient(profile)

            # 2. Break down into scenes
            scene_stage = SceneStage(ai_client=ai_client)
            prompt_stage = ImagePromptStage(
                ai_client=ai_client,
                batch_size=5,
                max_concurrency=min(3, max_concurrent)
            )

            logger.info(f"Breaking down script for project folder '{folder.name}' into visual scenes...")
            input_for_scene = srt_chunks if srt_chunks else script_text
            scenes_data = await scene_stage.process(input_for_scene, preset)

            # 3. Generate detailed image prompts
            logger.info(f"Generating style-locked scene image prompts for '{folder.name}' under preset '{preset_name}'...")
            prompts, continuity = await prompt_stage.process(scenes_data, preset, topic)

            package = GenerationPackage(
                topic=topic,
                preset_name=preset_name,
                title=folder.name,
                normalized_title=folder.name,
                script=script_text,
                prompts=prompts,
                continuity=continuity
            )

            # 4. Write prompts.txt into the folder
            ContentExporter.write_prompts_to_existing_project(folder, package)
            logger.info(f"Successfully generated prompts.txt for '{folder.name}'!")

            result = {
                "folder": str(folder),
                "prompts_count": len(prompts),
                "status": "COMPLETED"
            }
            self.finished_signal.emit(str(folder), result)

        except Exception as e:
            logger.exception(f"Failed generating prompts for folder '{folder.name}': {e}")
            self.failed_signal.emit(str(folder), str(e))
