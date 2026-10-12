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
            # Fallback simple fixes
            # Remove trailing commas
            cleaned = re.sub(r",\s*([\]}])", r"\1", potential_json)
            return json.loads(cleaned)

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

