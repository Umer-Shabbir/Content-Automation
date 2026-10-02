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
