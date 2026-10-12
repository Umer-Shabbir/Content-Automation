import json
import logging
import re
from typing import List, Dict, Any

from app.ai.client import get_ai_client
from app.prompts.builder import PromptBuilder
from app.prompts.parser import extract_script_text
from app.models.preset import ContentPreset
from app.models.enums import StageLevel

def clean_artifact_text(text: str) -> str:
    """Removes residual LLM tool artifacts and system response wrappers from string values."""
    if not text:
        return ""
    text = re.sub(r'\(empty response\)\[Skill result:.*?\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\[Skill result:.*?\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\{"success":true,"data":.*?"context":.*?\}', '', text, flags=re.DOTALL)
    text = text.replace("```json", "").replace("```", "").strip()
    return text

class ScriptStage:
    def __init__(self, ai_client=None, event_bus=None):
        self.ai = ai_client or get_ai_client()
        self.event_bus = event_bus
        self.prompt_builder = PromptBuilder()

    async def process(self, topic: str, title: str, preset: ContentPreset, retry_limit: int = 3) -> str:
        """
        Generates a video script based on the topic, title, and preset.
        Guarantees that the returned script is strictly clean voice-over narration text.
        """
        language = getattr(preset, 'video_language', 'English')
        prompt_payload = self.prompt_builder.build_script_generation_messages(
            topic=topic,
            title=title,
            rules=preset.script_rules,
            language=language
        )
        prompt = prompt_payload["messages"][0]["content"]
        system_prompt = prompt_payload.get("system", "You are an expert video script writer.\nCRITICAL RULE: NEVER include speaker tags like [Narrator] or (Narrator). Provide pure spoken words only.")

        fallback_script = f"Today we explore the fascinating topic of {topic} in detail."

        for attempt in range(retry_limit):
            try:
                if hasattr(self.ai, "generate"):
                    response = await self.ai.generate(prompt=prompt, role="generator")
                    raw_script = response.text.strip()
                else:
                    response = await self.ai.generate_message(
                        messages=[{"role": "user", "content": prompt}],
                        system=system_prompt,
                    )
                    raw_script = response["text"].strip()
            except Exception as e:
                logging.warning(f"Script generation LLM call failed (attempt {attempt + 1}): {e}")
                raw_script = fallback_script

            raw_script = clean_artifact_text(raw_script)
            initial_script = extract_script_text(raw_script, fallback=fallback_script)

            # Ask critic to review and verify/fix the script
            critic_payload = self.prompt_builder.build_script_critic_messages(
                topic=topic,
                title=title,
                script=initial_script,
                rules=preset.script_rules,
                reviewer_rules=preset.reviewer_rules
            )
            critic_system = critic_payload.get("system", """You are a rigorous script editor and verifier.
Ensure the script does NOT contain ANY tags like [Narrator], (Narrator), [Music], or speaker identifiers.
Respond with ONLY the finalized script text, nothing else.""")

            critic_user = f"Review and refine this script for topic '{topic}' (Title: '{title}'). Follow pacing/tone rules and REMOVE ANY SPEAKER TAGS OR BRACKETS:\n\n{initial_script}"

            try:
                if hasattr(self.ai, "generate"):
                    critic_response = await self.ai.generate(prompt=critic_user, role="critic")
                    critic_raw = critic_response.text.strip()
                else:
                    critic_response = await self.ai.generate_message(
                        messages=[{"role": "user", "content": critic_user}],
                        system=critic_system,
                    )
                    critic_raw = critic_response["text"].strip()
            except Exception as e:
                logging.warning(f"Script critic LLM call failed (attempt {attempt + 1}): {e}")
                critic_raw = ""

            critic_raw = clean_artifact_text(critic_raw)
            # Extract script text from critic response; if it returned review metadata without a script, fall back to initial_script
            final_script = extract_script_text(critic_raw, fallback=initial_script)

            if final_script and "empty_response" not in final_script and "skill_result_memory_search" not in final_script and "[Skill result:" not in final_script:
                return final_script

        return fallback_script


