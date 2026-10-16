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

def sanitize_voiceover_script(text: str) -> str:
    """Strips residual speaker tags, stage directions, and parentheticals from voiceover narration."""
    if not text:
        return ""
    # Strip speaker labels like [Narrator], Narrator:, Host:, [Voiceover], Voiceover:
    text = re.sub(r'^(?:\[?(?:Narrator|Voiceover|Host|Speaker\s*\d*)\]?:?)\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    # Strip bracketed stage directions like [Music], [Sound effect], [Pause], [Dramatic tone]
    text = re.sub(r'\[(?:Music|Sound|Pause|Tone|Visual|SFX|Beat|Laughter|Applause|Cut to|Fade to).*?\]', '', text, flags=re.IGNORECASE)
    # Strip parenthetical production directions like (pause), (dramatic music rises)
    text = re.sub(r'\((?:pause|dramatic|whispering|softly|loudly|music|tone|sfx).*?\)', '', text, flags=re.IGNORECASE)
    # Clean multi-spaces
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text).strip()
    return text

class ScriptStage:
    def __init__(self, ai_client=None, event_bus=None):
        self.ai = ai_client or get_ai_client()
        self.event_bus = event_bus
        self.prompt_builder = PromptBuilder()

    async def process(self, topic: str, title: str, preset: ContentPreset, retry_limit: int = 3) -> str:
        """
        Generates a video script based on the topic, title, and preset.
        Guarantees that the returned script is strictly clean voice-over narration text
        optimized for high YouTube retention.
        """
        from app.prompts.parser import extract_json

        language = getattr(preset, 'video_language', 'English')
        fallback_script = (
            f"In the high-stakes story of {topic}, a single fatal miscalculation changed everything. "
            f"What followed was a catastrophe that nobody saw coming, permanently reshaping the landscape. "
            f"Here is the untold story of how it unfolded."
        )

        current_feedback = None
        current_draft = None

        for attempt in range(retry_limit):
            prompt_payload = self.prompt_builder.build_script_generation_messages(
                topic=topic,
                title=title,
                rules=preset.script_rules,
                feedback=current_feedback,
                previous_draft=current_draft,
                language=language
            )
            prompt = prompt_payload["messages"][-1]["content"] if attempt > 0 else prompt_payload["messages"][0]["content"]
            system_prompt = prompt_payload.get("system", "You are an expert video script writer.\nCRITICAL RULE: NEVER include speaker tags like [Narrator] or (Narrator). Provide pure spoken words only.")

            try:
                if hasattr(self.ai, "generate"):
                    response = await self.ai.generate(prompt=prompt, role="generator")
                    raw_script = response.text.strip()
                else:
                    response = await self.ai.generate_message(
                        messages=prompt_payload["messages"],
                        system=system_prompt,
                    )
                    raw_script = response["text"].strip()
            except Exception as e:
                logging.warning(f"Script generation LLM call failed (attempt {attempt + 1}): {e}")
                raw_script = fallback_script

            raw_script = clean_artifact_text(raw_script)
            initial_script = extract_script_text(raw_script, fallback=fallback_script)
            initial_script = sanitize_voiceover_script(initial_script)

            # Ask critic to review and retention-audit the script
            critic_payload = self.prompt_builder.build_script_critic_messages(
                topic=topic,
                title=title,
                script=initial_script,
                rules=preset.script_rules,
                reviewer_rules=preset.reviewer_rules
            )
            critic_system = critic_payload.get("system", "")
            critic_user = critic_payload["messages"][0]["content"]

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

            # Check if critic returned structured JSON audit
            decision = "APPROVE"
            critic_feedback = ""
            critic_refined = ""
            try:
                critic_json = extract_json(critic_raw)
                if isinstance(critic_json, dict):
                    decision = str(critic_json.get("decision", "APPROVE")).upper()
                    critic_feedback = str(critic_json.get("feedback", "")).strip()
                    score = float(critic_json.get("score", 90))
                    min_q = getattr(preset.reviewer_rules, "min_quality_score", 8.0)
                    if score < min_q and decision != "REVISE":
                        decision = "REVISE"
                    critic_refined = critic_json.get("refined_script") or critic_json.get("script") or ""
                    if isinstance(critic_refined, str):
                        critic_refined = critic_refined.strip()
            except Exception:
                pass

            # If critic provided a refined script or raw replacement, extract it
            if not critic_refined:
                critic_refined = extract_script_text(critic_raw, fallback="")

            candidate = critic_refined if (critic_refined and len(critic_refined.split()) > 20) else initial_script
            candidate = sanitize_voiceover_script(candidate)

            # Check if ready to return
            if (decision == "APPROVE" or attempt == retry_limit - 1) and candidate:
                if "empty_response" not in candidate and "[Skill result:" not in candidate:
                    return candidate

            # Otherwise, loop with feedback to revise
            current_feedback = critic_feedback or "Improve retention: sharpen the opening hook, eliminate throat-clearing, and inject pattern interrupts every 30-45 seconds."
            current_draft = candidate

        return fallback_script


