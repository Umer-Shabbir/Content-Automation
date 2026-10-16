import json
from typing import Dict, List, Any

from app.models.preset import TitleRules, ScriptRules, ImageRules, ReviewerRules, ContentPreset
from app.models.generation import ScenePrompt, VisualContinuityState, GenerationPackage
from app.prompts import templates

class PromptBuilder:
    """Builds prompt payloads for the LLM client by injecting parameters into templates"""

    @staticmethod
    def _create_payload(system_prompt: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        return {
            "system": system_prompt.strip(),
            "messages": messages
        }

    @staticmethod
    def build_title_generation_messages(topic: str, rules: TitleRules) -> Dict[str, Any]:
        rules_text = (
            f"Structure: {rules.title_structure}\n"
            f"Hook Style: {rules.hook_style}\n"
            f"Curiosity Level (1-10): {rules.curiosity_level}\n"
            f"Clickability Guidance: {rules.clickability_guidance}\n"
            f"Topic Relevance: {rules.topic_relevance}\n"
            f"Forbidden Patterns (DO NOT USE): {', '.join(rules.forbidden_patterns)}"
        )
        user_content = templates.TITLE_GENERATION_USER.format(topic=topic, rules=rules_text)
        return PromptBuilder._create_payload(
            templates.TITLE_GENERATION_SYSTEM,
            [{"role": "user", "content": user_content.strip()}]
        )

    @staticmethod
    def build_title_critic_messages(topic: str, candidates: List[str], rules: TitleRules, reviewer_rules: ReviewerRules) -> Dict[str, Any]:
        candidates_xml = "<candidates>\n" + "\n".join(f"<candidate>{c}</candidate>" for c in candidates) + "\n</candidates>"
        rules_text = (
            f"Structure: {rules.title_structure}\n"
            f"Hook Style: {rules.hook_style}\n"
            f"Curiosity Level (1-10): {rules.curiosity_level}"
        )
        rev_rules_text = f"Minimum acceptable quality score: {reviewer_rules.min_quality_score}"

        user_content = templates.TITLE_CRITIC_USER.format(
            topic=topic,
            candidates_xml=candidates_xml,
            rules=rules_text,
            reviewer_rules=rev_rules_text
        )
        return PromptBuilder._create_payload(
            templates.TITLE_CRITIC_SYSTEM,
            [{"role": "user", "content": user_content.strip()}]
        )

    @staticmethod
    def build_script_generation_messages(
        topic: str, title: str, rules: ScriptRules, feedback: str = None, previous_draft: str = None, language: str = "English"
    ) -> Dict[str, Any]:
        rules_text = (
            f"Narrative Structure: {rules.narrative_structure}\n"
            f"Tone: {rules.tone}\n"
            f"Pacing: {rules.pacing}\n"
            f"Target Word Count: {rules.target_words}\n"
            f"Strict Voiceover Only: {'YES! NO STAGE DIRECTIONS ALLOWED. SPEAKER TAGS (e.g. [Narrator]) ARE FORBIDDEN.' if rules.strict_voiceover_only else 'Normal Voiceover'}"
        )
        user_content = templates.SCRIPT_GENERATION_USER.format(
            topic=topic, title=title, language=language, rules=rules_text
        )

        messages = [{"role": "user", "content": user_content.strip()}]

        if feedback and previous_draft:
            messages.append({"role": "assistant", "content": previous_draft})
            feedback_msg = f"<critic_feedback>\n{feedback}\n</critic_feedback>\n\nPlease revise the script following all rules. Do not include stage directions!"
            messages.append({"role": "user", "content": feedback_msg})

        return PromptBuilder._create_payload(templates.SCRIPT_GENERATION_SYSTEM, messages)

    @staticmethod
    def build_script_critic_messages(
        topic: str, title: str, script: str, rules: ScriptRules, reviewer_rules: ReviewerRules
    ) -> Dict[str, Any]:
        rules_text = (
            f"Target Word Count: {rules.target_words}\n"
            f"Tone: {rules.tone}"
        )
        rev_rules_text = (
            f"Minimum quality score: {reviewer_rules.min_quality_score}\n"
            f"Require voiceover cleanliness (NO stage directions): {reviewer_rules.require_voiceover_cleanliness}"
        )

        user_content = templates.SCRIPT_CRITIC_USER.format(
            topic=topic, title=title, script=script.strip(),
            rules=rules_text, reviewer_rules=rev_rules_text
        )
        return PromptBuilder._create_payload(
            templates.SCRIPT_CRITIC_SYSTEM,
            [{"role": "user", "content": user_content.strip()}]
        )

    @staticmethod
    def build_scene_planning_messages(topic: str, title: str, script: str, image_rules: ImageRules, srt_chunks_xml: str = "") -> Dict[str, Any]:
        img_rules_text = (
            f"Visual Style: {image_rules.visual_style}\n"
            f"Cinematic Style: {image_rules.cinematic_style}\n"
            f"Scene Density: {image_rules.scene_density}"
        )

        # Use provided srt chunks directly. If empty, fallback to passing the raw script.
        user_content = templates.SCENE_PLANNER_USER.format(
            topic=topic, srt_chunks_xml=srt_chunks_xml or script.strip(), image_rules=img_rules_text
        )
        return PromptBuilder._create_payload(
            templates.SCENE_PLANNER_SYSTEM,
            [{"role": "user", "content": user_content.strip()}]
        )

    @staticmethod
    def build_image_prompts_messages(
        topic: str, title: str, script: str, scenes: List[Dict[str, Any]],
        continuity: VisualContinuityState, image_rules: ImageRules, feedback: str = None
    ) -> Dict[str, Any]:

        scenes_xml = "<scenes>\n"
        for idx, scene in enumerate(scenes):
            scenes_xml += f"<scene index='{idx}'>\n{json.dumps(scene, indent=2)}\n</scene>\n"
        scenes_xml += "</scenes>"

        continuity_json = continuity.model_dump_json(indent=2)

        img_rules_text = (
            f"Visual Style: {image_rules.visual_style}\n"
            f"Cinematic Style: {image_rules.cinematic_style}\n"
            f"Aspect Ratio: {image_rules.aspect_ratio}\n"
            f"Character Consistency Rule: {image_rules.character_consistency}\n"
            f"Environment Consistency Rule: {image_rules.environment_consistency}"
        )

        user_content = templates.IMAGE_PROMPT_GENERATION_USER.format(
            script=script.strip(), scenes_xml=scenes_xml,
            continuity=continuity_json, image_rules=img_rules_text
        )

        messages = [{"role": "user", "content": user_content.strip()}]

        if feedback:
            messages.append({"role": "assistant", "content": "Here are the previous prompts..."})
            messages.append({"role": "user", "content": f"<feedback>{feedback}</feedback>\nPlease revise."})

        return PromptBuilder._create_payload(templates.IMAGE_PROMPT_GENERATION_SYSTEM, messages)

    @staticmethod
    def build_image_prompts_critic_messages(
        script: str, prompts: List[Dict[str, Any]],
        continuity: VisualContinuityState, image_rules: ImageRules, reviewer_rules: ReviewerRules
    ) -> Dict[str, Any]:

        prompts_xml = "<prompts>\n"
        for p in prompts:
            prompts_xml += f"<prompt>\n{json.dumps(p, indent=2)}\n</prompt>\n"
        prompts_xml += "</prompts>"

        continuity_json = continuity.model_dump_json(indent=2)

        img_rules_text = (
            f"Visual Style: {image_rules.visual_style}\n"
            f"Character Consistency Rule: {image_rules.character_consistency}"
        )

        rev_rules_text = (
            f"Require strict continuity compliance: {reviewer_rules.require_continuity}\n"
            f"Minimum Acceptable Score: {reviewer_rules.min_quality_score}"
        )

        user_content = templates.IMAGE_PROMPT_CRITIC_USER.format(
            prompts_xml=prompts_xml, continuity=continuity_json,
            image_rules=img_rules_text, reviewer_rules=rev_rules_text
        )

        return PromptBuilder._create_payload(
            templates.IMAGE_PROMPT_CRITIC_SYSTEM,
            [{"role": "user", "content": user_content.strip()}]
        )

    @staticmethod
    def build_final_review_messages(package: GenerationPackage, preset: ContentPreset) -> Dict[str, Any]:
        user_content = templates.FINAL_REVIEW_USER.format(
            package_json=package.model_dump_json(indent=2),
            preset_json=preset.model_dump_json(indent=2)
        )
        return PromptBuilder._create_payload(
            templates.FINAL_REVIEW_SYSTEM,
            [{"role": "user", "content": user_content.strip()}]
        )

    @staticmethod
    def build_thumbnail_prompts_messages(
        topic: str, title: str, preset: ContentPreset, art_style_anchor: str = ""
    ) -> Dict[str, Any]:
        styles_desc_lines = []
        for i, s in enumerate(preset.thumbnail_styles, 1):
            styles_desc_lines.append(f"Style {i} ({s.id}): {s.name}\nGuidelines: {s.description}\n")
        styles_description = "\n".join(styles_desc_lines)

        user_content = templates.THUMBNAIL_PROMPTS_GENERATION_USER.format(
            title=title,
            topic=topic,
            art_style_anchor=art_style_anchor or preset.image_rules.visual_style,
            styles_description=styles_description
        )
        return PromptBuilder._create_payload(
            templates.THUMBNAIL_PROMPTS_GENERATION_SYSTEM,
            [{"role": "user", "content": user_content.strip()}]
        )

    def build(self, level, preset, inputs: dict) -> str:
        """
        Generic compatibility dispatcher for building single string prompts.
        """
        topic = inputs.get("topic", "")
        title = inputs.get("title", "")
        script = inputs.get("script", "")
        scenes = inputs.get("scenes", "")

        level_str = str(level).upper()
        if "TITLE" in level_str:
            res = self.build_title_generation_messages(topic, preset.title_rules)
            return res["messages"][0]["content"]
        elif "SCRIPT" in level_str:
            res = self.build_script_generation_messages(topic, title, preset.script_rules)
            return res["messages"][0]["content"]
        elif "SCENE" in level_str:
            srt_chunks_xml = inputs.get("srt_chunks_xml", "")
            res = self.build_scene_planning_messages(topic, title, script, preset.image_rules, srt_chunks_xml)
            return res["messages"][0]["content"]
        elif "IMAGE" in level_str:
            # Generate continuity / prompts
            return f"Topic: {topic}\nScript: {script}\nScenes: {scenes}"
        else:
            return f"Topic: {topic}\nRules: {preset}"
