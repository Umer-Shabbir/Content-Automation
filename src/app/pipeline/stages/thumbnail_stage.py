import json
import re
import inspect
import logging
from typing import List, Dict, Any, Optional

from app.ai.client import get_ai_client
from app.prompts.builder import PromptBuilder
from app.prompts.parser import extract_json
from app.models.preset import ContentPreset
from app.models.generation import GenerationPackage
from app.storage.exporter import ContentExporter

logger = logging.getLogger(__name__)


class ThumbnailStage:
    """
    Two-step Generator + Critic pipeline for world-class, research-backed YouTube thumbnails.
    
    1. Generator: Generates candidate thumbnail prompts based on the preset's 3 distinct styles,
       incorporating focal dominance, visual hierarchy, curiosity gap, split-complementary lighting,
       and zero-text purity.
    2. Critic: Evaluates candidate prompts against scientific mobile CTR criteria (35-50% subject dominance,
       narrative clash, chiaroscuro/dynamic contrast, zero text) and refines them into top-tier prompts.
    """

    def __init__(self, ai_client=None):
        self.ai = ai_client or get_ai_client()

    async def _call_llm(self, payload: Dict[str, Any], role: str = "generator") -> str:
        prompt_content = payload["messages"][0]["content"]
        system_prompt = payload.get("system", "")

        if hasattr(self.ai, "generate_message"):
            res = self.ai.generate_message(
                messages=[{"role": "user", "content": prompt_content}],
                system=system_prompt
            )
            response = await res if inspect.isawaitable(res) else res
            if isinstance(response, dict) and isinstance(response.get("text"), str):
                return response["text"].strip()
            elif isinstance(response, str):
                return response.strip()
            return ""
        elif hasattr(self.ai, "generate"):
            res = self.ai.generate(prompt=prompt_content, role=role)
            response = await res if inspect.isawaitable(res) else res
            if hasattr(response, "text") and isinstance(response.text, str):
                return response.text.strip()
            elif isinstance(response, str):
                return response.strip()
            return ""
        return ""

    async def process(self, package: GenerationPackage, preset: ContentPreset) -> List[str]:
        default_data = ContentExporter._get_or_generate_thumbnail_prompts(package, preset)
        fallback_prompts = [item["prompt"] for item in default_data]

        if not self.ai:
            return fallback_prompts

        anchor = ""
        if hasattr(package, "continuity") and package.continuity and package.continuity.art_style_anchor:
            anchor = package.continuity.art_style_anchor
        elif hasattr(preset, "image_rules") and hasattr(preset.image_rules, "visual_style"):
            anchor = preset.image_rules.visual_style
        elif hasattr(preset, "visual_style"):
            anchor = preset.visual_style

        # Step 1: Candidate Generation
        candidates = await self._generate_candidates(package, preset, anchor, fallback_prompts)

        # Step 2: Critic Step (Evaluate and Refine)
        refined = await self._critique_and_refine(package, preset, anchor, candidates)

        # Step 3: Polish and enforce constraints (zero text, style lock)
        final_prompts = []
        for i, prompt_text in enumerate(refined):
            clean_prompt = self._enforce_thumbnail_rules(prompt_text, anchor)
            final_prompts.append(clean_prompt)

        return final_prompts

    async def _generate_candidates(
        self, package: GenerationPackage, preset: ContentPreset, anchor: str, fallback_prompts: List[str]
    ) -> List[Dict[str, Any]]:
        styles = getattr(preset, "thumbnail_styles", []) or []

        try:
            payload = PromptBuilder.build_thumbnail_prompts_messages(
                topic=package.topic,
                title=package.title,
                preset=preset,
                art_style_anchor=anchor
            )
            raw_text = await self._call_llm(payload, role="generator")
            parsed = extract_json(raw_text)

            if isinstance(parsed, dict):
                for k in ["thumbnail_prompts", "thumbnails", "prompts", "candidates"]:
                    if isinstance(parsed.get(k), list):
                        parsed = parsed[k]
                        break

            if isinstance(parsed, list) and len(parsed) >= 1:
                candidates = []
                for idx, item in enumerate(parsed[:3]):
                    style_id = styles[idx].id if idx < len(styles) else f"style_{idx+1}"
                    style_name = styles[idx].name if idx < len(styles) else f"Style {idx+1}"

                    if isinstance(item, dict):
                        p_text = item.get("thumbnail_prompt") or item.get("prompt") or item.get("text") or ""
                        s_id = item.get("style_id", style_id)
                        s_name = item.get("style_name", style_name)
                    elif isinstance(item, str):
                        p_text = item
                        s_id = style_id
                        s_name = style_name
                    else:
                        p_text = ""
                        s_id = style_id
                        s_name = style_name

                    p_text = p_text.strip() if p_text else (fallback_prompts[idx] if idx < len(fallback_prompts) else "")
                    candidates.append({
                        "style_id": s_id,
                        "style_name": s_name,
                        "thumbnail_prompt": p_text
                    })

                while len(candidates) < 3 and len(candidates) < len(fallback_prompts):
                    idx = len(candidates)
                    candidates.append({
                        "style_id": styles[idx].id if idx < len(styles) else f"style_{idx+1}",
                        "style_name": styles[idx].name if idx < len(styles) else f"Style {idx+1}",
                        "thumbnail_prompt": fallback_prompts[idx]
                    })

                if len(candidates) == 3:
                    return candidates
        except Exception as e:
            logger.warning(f"Thumbnail candidate generation failed: {e}")

        # Fallback candidates
        result = []
        for idx in range(min(3, len(fallback_prompts))):
            result.append({
                "style_id": styles[idx].id if idx < len(styles) else f"style_{idx+1}",
                "style_name": styles[idx].name if idx < len(styles) else f"Style {idx+1}",
                "thumbnail_prompt": fallback_prompts[idx]
            })
        return result

    async def _critique_and_refine(
        self, package: GenerationPackage, preset: ContentPreset, anchor: str, candidates: List[Dict[str, Any]]
    ) -> List[str]:
        default_prompts = [c["thumbnail_prompt"] for c in candidates]

        try:
            critic_payload = PromptBuilder.build_thumbnail_critic_messages(
                topic=package.topic,
                title=package.title,
                candidates=candidates,
                preset=preset,
                art_style_anchor=anchor
            )
            raw_text = await self._call_llm(critic_payload, role="critic")
            parsed = extract_json(raw_text)

            refined_list = []
            if isinstance(parsed, dict):
                evaluated = parsed.get("evaluated_thumbnails") or parsed.get("thumbnails") or parsed.get("candidates")
                if isinstance(evaluated, list) and len(evaluated) >= 1:
                    for idx, item in enumerate(evaluated[:3]):
                        if isinstance(item, dict):
                            p = item.get("refined_prompt") or item.get("thumbnail_prompt") or item.get("prompt")
                        elif isinstance(item, str):
                            p = item
                        else:
                            p = ""

                        if p and isinstance(p, str) and p.strip():
                            refined_list.append(p.strip())
                        elif idx < len(default_prompts):
                            refined_list.append(default_prompts[idx])

            if len(refined_list) == len(default_prompts):
                return refined_list
        except Exception as e:
            logger.warning(f"Thumbnail critique failed: {e}")

        return default_prompts

    def _enforce_thumbnail_rules(self, prompt: str, anchor: str) -> str:
        """
        Enforces:
        1. Strict Zero text rule (strip text-rendering instructions, quotes, signage requests)
        2. Visual style lock
        """
        cleaned = prompt.strip()
        # Remove patterns like: text: "...", with text "...", typography reading "...", words reading "...", sign says "..."
        cleaned = re.sub(r'(?i)\b(with\s+)?(text|typography|words?|letters?|letters\s+reading|quote|title|headline|label|caption|sign|signage)\s*(?:that\s+says|reading|displaying|written|saying)?\s*[:=]?\s*["\'][^"\']+["\']', '', cleaned)
        cleaned = re.sub(r'(?i)\bwith\s+bold\s+text\b.*?(?:,|$)', '', cleaned)
        cleaned = re.sub(r'(?i)\bwith\s+(?:the\s+)?text\s+["\'][^"\']+["\']', '', cleaned)
        cleaned = re.sub(r'(?i)\b(?:showing|displaying|featuring)\s+the\s+words?\s+["\'][^"\']+["\']', '', cleaned)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip(' ,;')

        # Enforce style anchor
        if anchor and anchor.lower() not in cleaned.lower():
            cleaned = f"{cleaned}, {anchor}"

        return cleaned
