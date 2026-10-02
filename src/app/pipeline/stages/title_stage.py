import json
import logging
from typing import List, Dict, Any, Tuple
from app.ai.client import AnthropicClient, get_ai_client
from app.prompts.builder import PromptBuilder
from app.models.preset import ContentPreset
from app.models.enums import StageLevel

class DuplicateFilter:
    def __init__(self):
        self._history = set()

    def is_duplicate(self, title: str) -> bool:
        return title.lower().strip() in self._history

    def record(self, title: str):
        self._history.add(title.lower().strip())

class TitleStage:
    def __init__(self, duplicate_filter=None, ai_client=None, event_bus=None):
        # We allow dependency injection or construct a default filter
        self.duplicate_filter = duplicate_filter or DuplicateFilter()

        # In the context of orchestration tests they pass ai_client directly
        # but in actual runtime we might fetch it.
        # Handling the existing test mock shape
        self.ai = ai_client or get_ai_client()

        # Instantiate Prompts Builder if needed but we'll use raw prompt mostly for compatibility
        self.prompt_builder = PromptBuilder()

    async def process(self, topic: str, preset: ContentPreset, retry_limit: int = 3) -> str:
        """
        Generates title candidates -> evaluates uniqueness -> picks best.
        """
        for _ in range(retry_limit):
            prompt = self.prompt_builder.build_title_generation_messages(topic=topic, rules=preset.title_rules)["messages"][0]["content"]

            # Use generator role explicitly using the ai_client which could be mocked
            # AnthropicClient mock has generate_message, not .generate() yet or
            # uses the wrapper. We must use what test expects.
            if hasattr(self.ai, "generate"):
                response = await self.ai.generate(prompt=prompt, role="generator")
                text = response.text
            else:
                response = await self.ai.generate_message(
                    messages=[{"role": "user", "content": prompt}],
                    system="You are an expert YouTube title generator. Reply ONLY with a valid JSON array of 5 title strings.",
                )
                text = response["text"]

            # Parse response
            titles = self._parse_titles(text)

            # Ask critic
            critic_prompt = f"Evaluate these titles for a YouTube video about {topic}: {json.dumps(titles)}. " \
                           f"Return the best one. Do not output anything else, no quotes, no conversational text."

            # Call critic role
            if hasattr(self.ai, "generate"):
                critic_response = await self.ai.generate(prompt=critic_prompt, role="critic")
                best_title = critic_response.text.strip(' "\'')
            else:
                critic_response = await self.ai.generate_message(
                    messages=[{"role": "user", "content": critic_prompt}],
                    system="You are a YouTube Title Critic. Select the best performing title. Output exactly the title string.",
                )
                best_title = critic_response["text"].strip(' "\'')

            if not self.duplicate_filter.is_duplicate(best_title):
                self.duplicate_filter.record(best_title)
                return best_title

        # Fallback if we couldn't get a unique one
        fallback = best_title if 'best_title' in locals() else f"Amazing video about {topic}"
        self.duplicate_filter.record(fallback)
        return fallback

    def _parse_titles(self, text: str) -> List[str]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return [line.strip(' -*\'"') for line in text.split('\n') if line.strip()]
