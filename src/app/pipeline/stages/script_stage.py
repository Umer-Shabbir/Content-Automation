import json
import logging
from typing import List, Dict, Any

from app.ai.client import get_ai_client
from app.prompts.builder import PromptBuilder

from app.models.preset import ContentPreset
from app.models.enums import StageLevel

class ScriptStage:
    def __init__(self, ai_client=None, event_bus=None):
        self.ai = ai_client or get_ai_client()
        self.event_bus = event_bus
        self.prompt_builder = PromptBuilder()

    async def process(self, topic: str, title: str, preset: ContentPreset) -> str:
        """
        Generates a video script based on the topic, title, and preset.
        """
        prompt = self.prompt_builder.build(
            level=StageLevel.SCRIPT,
            preset=preset,
            inputs={"topic": topic, "title": title}
        )

        if hasattr(self.ai, "generate"):
            response = await self.ai.generate(prompt=prompt, role="generator")
            script = response.text.strip()
        else:
            response = await self.ai.generate_message(
                messages=[{"role": "user", "content": prompt}],
                system="You are an expert video script writer.",
            )
            script = response["text"].strip()

        return script
