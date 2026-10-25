import json
import logging
import re
import asyncio
from typing import List, Dict, Any, Tuple, Optional
from app.ai.client import AnthropicClient, get_ai_client
from app.prompts.builder import PromptBuilder
from app.prompts.parser import extract_json
from app.models.preset import ContentPreset
from app.models.enums import StageLevel
from app.pipeline.duplicate_checker import DuplicateFilter

ARTIFACT_KEYWORDS = [
    "empty_response",
    "skill_result",
    "memory_search",
    "[skill result:",
    "[skill_result",
    "successtrue",
    "totaltokens",
    "\"success\":",
    "\"data\":",
    "\"context\":",
    "\"memories\":",
    "```",
]

def clean_artifact_text(text: str) -> str:
    """Removes residual LLM tool artifacts and system response wrappers from string values."""
    if not text:
        return ""
    text = re.sub(r'\(empty response\)\[Skill result:.*?\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\[Skill result:.*?\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\{"success":true,"data":.*?"context":.*?\}', '', text, flags=re.DOTALL)
    text = text.replace("```json", "").replace("```", "").strip()
    return text

def is_valid_title(title: str) -> bool:
    """Checks whether a string is a clean, single-line, valid video title."""
    if not title or not isinstance(title, str):
        return False
    t = title.strip().lower()
    if len(t) < 5 or len(t) > 150:
        return False
    if "\n" in title or "\r" in title:
        return False
    for kw in ARTIFACT_KEYWORDS:
        if kw in t:
            return False
    if t.startswith("{") or t.startswith("[") or t.endswith("}") or t.endswith("]"):
        return False
    return True

def clean_title_string(title: str) -> str:
    """Cleans unwanted quotes, markdown symbols, prefixes, and newlines from a title."""
    if not title:
        return ""
    title = clean_artifact_text(title)
    # Strip quotes, backticks, leading list numbers like "1. ", "- "
    cleaned = title.strip(' "\'```')
    cleaned = re.sub(r'^(?:\d+[\.\)]|\-|\*)\s*', '', cleaned)
    # Replace any newlines with spaces
    cleaned = re.sub(r'[\r\n]+', ' ', cleaned)
    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

class TitleStage:
    def __init__(self, duplicate_filter=None, ai_client=None, event_bus=None, base_output_dir=None):
        self.duplicate_filter = duplicate_filter or DuplicateFilter(base_output_dir=base_output_dir)
        self.ai = ai_client or get_ai_client()
        self.prompt_builder = PromptBuilder()
        self.base_output_dir = base_output_dir

    async def fetch_seo_data(self, query: str) -> Tuple[List[str], List[str]]:
        """
        Uses suggestqueries.google.com to fetch tags and suggestions for YouTube SEO context.
        Uses non-blocking async HTTP with a strict 3-second timeout so it never hangs or blocks threads.
        """
        import urllib.parse
        import httpx
        tags, related = [], []
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                url1 = f"https://suggestqueries.google.com/complete/search?client=youtube&ds=yt&client=firefox&q={urllib.parse.quote(query)}"
                url2 = f"https://suggestqueries.google.com/complete/search?client=chrome&q={urllib.parse.quote(query + ' youtube')}"

                res1, res2 = await asyncio.gather(
                    client.get(url1, headers=headers),
                    client.get(url2, headers=headers),
                    return_exceptions=True
                )
                if not isinstance(res1, Exception) and hasattr(res1, "status_code") and res1.status_code == 200:
                    try:
                        data = res1.json()
                        tags = data[1] if len(data) > 1 else []
                    except Exception:
                        pass
                if not isinstance(res2, Exception) and hasattr(res2, "status_code") and res2.status_code == 200:
                    try:
                        data2 = res2.json()
                        related = data2[1] if len(data2) > 1 else []
                    except Exception:
                        pass
        except Exception as e:
            logging.debug(f"SEO suggestion fetch skipped or timed out: {e}")
        return tags, related

    async def process(self, topic: str, preset: ContentPreset, retry_limit: int = 5, base_output_dir: Optional[str] = None) -> Tuple[str, List[str], str]:
        """
        Generates title candidates -> evaluates uniqueness -> picks best.
        Returns: (best_title, tags, description)
        """
        output_dir = base_output_dir or self.base_output_dir
        tags, related = await self.fetch_seo_data(topic)
        seo_context = f"\nLive YouTube SEO Trends for this topic:\nTrending Tags: {', '.join(tags[:10])}\nRelated Intents: {', '.join(related[:10])}\n"

        best_title = ""
        description = ""

        for attempt in range(retry_limit):
            prompt = self.prompt_builder.build_title_generation_messages(topic=topic, rules=preset.title_rules)["messages"][0]["content"]
            prompt += seo_context + f"\nEnsure titles are unique and distinct (Attempt {attempt + 1}). Use live SEO trends for clickability."

            try:
                if hasattr(self.ai, "generate"):
                    response = await self.ai.generate(prompt=prompt, role="generator")
                    text = response.text
                else:
                    response = await self.ai.generate_message(
                        messages=[{"role": "user", "content": prompt}],
                        system="You are an expert YouTube title generator. Output ONLY a valid JSON list of 5 creative title objects or strings.",
                    )
                    text = response["text"]
            except Exception as e:
                logging.warning(f"Title generation LLM call failed (attempt {attempt + 1}): {e}")
                text = ""

            # Parse response safely
            titles = self._parse_titles(text)

            if not titles:
                # Dynamic fallback candidate based on preset hook or attempt count
                angle_prefix = ["The Truth About", "The Dark Side Of", "Why No One Talks About", "Inside The Collapse Of", "The Untold Story Of"][attempt % 5]
                fallback_candidate = clean_title_string(f"{angle_prefix} {topic.title()}")
                titles = [fallback_candidate]

            # Ask critic
            critic_prompt = f"Evaluate these candidate titles for a YouTube video about {topic}: {json.dumps(titles)}. " \
                           f"Return the single best title. Do not output anything else, no quotes, no conversational text."

            try:
                if hasattr(self.ai, "generate"):
                    critic_response = await self.ai.generate(prompt=critic_prompt, role="critic")
                    candidate_title = critic_response.text
                else:
                    critic_response = await self.ai.generate_message(
                        messages=[{"role": "user", "content": critic_prompt}],
                        system="You are a YouTube Title Critic. Select the best performing title. Output exactly the title string.",
                    )
                    candidate_title = critic_response["text"]
            except Exception as e:
                logging.warning(f"Title critic LLM call failed (attempt {attempt + 1}): {e}")
                candidate_title = titles[0]

            candidate_title = clean_title_string(candidate_title)

            if not is_valid_title(candidate_title):
                valid_candidates = [t for t in titles if is_valid_title(t)]
                if valid_candidates:
                    candidate_title = valid_candidates[0]
                else:
                    angle_prefix = ["The Secret Behind", "The Untold Truth Of", "How ONE Choice Destroyed"][attempt % 3]
                    candidate_title = clean_title_string(f"{angle_prefix} {topic.title()}")

            # Check duplicate status asynchronously or synchronously
            is_dup = False
            if hasattr(self.duplicate_filter, "is_duplicate"):
                res = self.duplicate_filter.is_duplicate(candidate_title, base_output_dir=output_dir)
                if asyncio.iscoroutine(res):
                    is_dup = await res
                else:
                    is_dup = bool(res)
            elif hasattr(self.duplicate_filter, "is_duplicate_sync"):
                is_dup = self.duplicate_filter.is_duplicate_sync(candidate_title, base_output_dir=output_dir)

            if not is_dup:
                best_title = candidate_title
                if hasattr(self.duplicate_filter, "record"):
                    self.duplicate_filter.record(best_title)

                # Generate SEO Description
                desc_prompt = f"Write a highly SEO-optimized YouTube video description (2-3 paragraphs max) for the video '{best_title}' on the topic '{topic}'. Include relevant keywords seamlessly. Do not include tags at the bottom. Return ONLY the description text."
                try:
                    if hasattr(self.ai, "generate"):
                        desc_response = await self.ai.generate(prompt=desc_prompt, role="generator")
                        description = desc_response.text.strip()
                    else:
                        desc_response = await self.ai.generate_message(
                            messages=[{"role": "user", "content": desc_prompt}],
                            system="You are an SEO expert. Reply ONLY with clean description text."
                        )
                        description = desc_response["text"].strip()
                except Exception as e:
                    logging.warning(f"Description LLM call failed: {e}")
                    description = f"An in-depth video story and explanation covering {topic}."

                description = clean_artifact_text(description)
                if not description:
                    description = f"An in-depth documentary exploring {topic} and the story behind {best_title}."

                final_tags = tags[:15] if tags else [topic, topic.replace(' ', ''), "story", "documentary", "explained"]
                return best_title, final_tags, description

        # Fallback if retry limit exceeded: make title unique by appending a distinct angle
        unique_suffix = f"- {preset.name.replace('_', ' ').title()} Edition" if hasattr(preset, 'name') else ""
        fallback = clean_title_string(f"The Truth About {topic.title()} {unique_suffix}")
        if hasattr(self.duplicate_filter, "record"):
            self.duplicate_filter.record(fallback)

        final_tags = tags[:15] if tags else [topic, topic.replace(' ', ''), "story", "documentary", "explained"]
        description = f"An amazing story and deep dive into {topic}."
        return fallback, final_tags, description

    def _parse_titles(self, text: str) -> List[str]:
        if not text:
            return []

        # Remove tool/skill artifacts
        cleaned_text = clean_artifact_text(text)
        if not cleaned_text:
            return []

        text_lower = cleaned_text.lower()
        for kw in ARTIFACT_KEYWORDS:
            if kw in text_lower:
                return []

        # Try using extract_json first
        try:
            parsed = extract_json(cleaned_text)
            if isinstance(parsed, list):
                extracted = []
                for item in parsed:
                    if isinstance(item, str):
                        extracted.append(clean_title_string(item))
                    elif isinstance(item, dict):
                        for k in ["title", "candidate", "name", "winner"]:
                            if k in item and isinstance(item[k], str):
                                extracted.append(clean_title_string(item[k]))
                                break
                valid = [t for t in extracted if is_valid_title(t)]
                if valid:
                    return valid
            elif isinstance(parsed, dict):
                candidates = parsed.get("titles") or parsed.get("candidates") or parsed.get("result") or []
                if isinstance(candidates, list):
                    extracted = []
                    for item in candidates:
                        if isinstance(item, str):
                            extracted.append(clean_title_string(item))
                        elif isinstance(item, dict):
                            for k in ["title", "candidate", "name"]:
                                if k in item and isinstance(item[k], str):
                                    extracted.append(clean_title_string(item[k]))
                                    break
                    valid = [t for t in extracted if is_valid_title(t)]
                    if valid:
                        return valid
                elif "winner" in parsed and isinstance(parsed["winner"], str):
                    t = clean_title_string(parsed["winner"])
                    if is_valid_title(t):
                        return [t]
        except Exception:
            pass

        # Fallback text line splitting
        clean_lines = []
        for line in cleaned_text.split('\n'):
            line_clean = clean_title_string(line)
            if is_valid_title(line_clean):
                clean_lines.append(line_clean)
        return clean_lines
