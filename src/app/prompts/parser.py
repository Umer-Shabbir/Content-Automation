import json
import re
from typing import Any, Dict, List, Optional, Union

def extract_json(text: str) -> Union[Dict[str, Any], List[Any]]:
    """
    Extracts and parses JSON from arbitrary LLM response text.
    Handles markdown code blocks (```json ... ```), raw JSON, and common LLM prefix text.
    """
    if not text:
        raise ValueError("Empty response text provided")

    # 1. Match code blocks ```json ... ``` or just ``` ... ```
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if code_block_match:
        content = code_block_match.group(1).strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

    # 2. Match raw array or object
    # Find the first '[' or '{' and the last ']' or '}'
    first_brace = text.find('{')
    first_bracket = text.find('[')

    start_idx = -1
    end_idx = -1

    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_idx = first_brace
        end_idx = text.rfind('}')
    elif first_bracket != -1:
        start_idx = first_bracket
        end_idx = text.rfind(']')

    if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
        potential_json = text[start_idx:end_idx+1]
        try:
            return json.loads(potential_json)
        except json.JSONDecodeError:
            # Fallback simple fixes: remove trailing commas
            cleaned = re.sub(r",\s*([\]}])", r"\1", potential_json)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    # If the first delimiter match failed, try the other delimiter type
    # For instance, if text started with a preamble containing '{' but the actual payload is an array '[ ... ]'
    if first_bracket != -1 and (start_idx != first_bracket):
        last_bracket = text.rfind(']')
        if last_bracket > first_bracket:
            bracket_json = text[first_bracket:last_bracket+1]
            try:
                return json.loads(bracket_json)
            except json.JSONDecodeError:
                cleaned = re.sub(r",\s*([\]}])", r"\1", bracket_json)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass
    elif first_brace != -1 and (start_idx != first_brace):
        last_brace = text.rfind('}')
        if last_brace > first_brace:
            brace_json = text[first_brace:last_brace+1]
            try:
                return json.loads(brace_json)
            except json.JSONDecodeError:
                cleaned = re.sub(r",\s*([\]}])", r"\1", brace_json)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass

    # Try parsing the whole string directly
    return json.loads(text)


def extract_tag_content(text: str, tag_name: str) -> Optional[str]:
    """
    Extracts the inner text of a specific XML tag from the LLM output.
    Example: extract_tag_content(response, "script") -> contents inside <script>...</script>
    """
    pattern = rf"<{tag_name}>(.*?)</{tag_name}>"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def extract_script_text(text: str, fallback: str = "") -> str:
    """
    Extracts pure voiceover narration script text from LLM outputs.
    Handles raw text, JSON wrapped text, markdown codeblocks, XML tags (<script> or <refined_script>),
    and filters out LLM reviewer evaluation metadata objects (e.g. {"review": ..., "decision": ...}).
    """
    if not text or not isinstance(text, str) or not text.strip():
        return fallback

    cleaned = text.strip()

    # 1. Try parsing JSON block or object
    try:
        data = extract_json(cleaned)
        if isinstance(data, dict):
            # Candidate keys where script text might live inside JSON
            for key in ["refined_script", "revised_script", "refined_short_form_script", "script", "final_script", "output_script", "spoken_text", "voiceover"]:
                val = data.get(key)
                if val and isinstance(val, str) and len(val.strip()) > 10:
                    val_str = val.strip()
                    # Check if val_str itself is not another raw JSON metadata string
                    if not (val_str.startswith("{") and ("review" in val_str or "decision" in val_str)):
                        cleaned = val_str
                        break
            else:
                # If dict has evaluation metadata but NO valid script key, return fallback
                if any(k in data for k in ["review", "decision", "evaluations", "recommendations", "hook_strength", "fatal_error_check"]):
                    return fallback
    except Exception:
        pass

    # 2. Extract XML tags if present (<script>...</script> or <refined_script>...</refined_script>)
    for tag in ["script", "refined_script", "refined_short_form_script", "voiceover", "final_script"]:
        tag_content = extract_tag_content(cleaned, tag)
        if tag_content:
            cleaned = tag_content
            break

    # 3. Strip markdown codeblock delimiters
    cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n?```$", "", cleaned, flags=re.MULTILINE)

    # 4. Filter out raw JSON strings that couldn't be parsed but start with '{' and have metadata keywords
    cleaned_lower = cleaned.lower()
    if cleaned.startswith("{") and ("\"review\"" in cleaned_lower or "\"decision\"" in cleaned_lower or "\"recommendations\"" in cleaned_lower):
        return fallback

    cleaned = cleaned.strip(' "\'\r\n\t')
    return cleaned if len(cleaned) > 5 else fallback


def extract_chapters_from_script(script: str) -> List[Dict[str, str]]:
    """
    Extracts structured chapters from a chapter-based script.
    Recognizes:
      [Chapter: <Title>]
      [Chapter 1: <Title>]
      Chapter 1: <Title>
      # Chapter 1: <Title>
    Returns list of dicts:
      [{"title": str, "first_sentence": str, "text": str}, ...]
    """
    if not script or not isinstance(script, str):
        return []

    chapter_pattern = re.compile(
        r'(?:^|\n)\s*(?:\[\s*Chapter(?:\s*\d+)?:\s*([^\]]+)\]|#*\s*Chapter\s+\d+[:\-]\s*([^\n]+))\s*(?:\n|\Z)',
        re.IGNORECASE
    )

    matches = list(chapter_pattern.finditer(script))
    if not matches:
        return []

    chapters = []
    for i, match in enumerate(matches):
        raw_title = match.group(1) or match.group(2) or f"Chapter {i+1}"
        title = raw_title.strip()

        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(script)
        body = script[start_pos:end_pos].strip()

        # Find the first meaningful sentence of the chapter body
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', body) if s.strip()]
        first_sentence = sentences[0] if sentences else body[:100]

        chapters.append({
            "title": title,
            "first_sentence": first_sentence,
            "text": body
        })

    return chapters


