TITLE_GENERATION_SYSTEM = """
You are an expert YouTube title copywriter. Your goal is to generate list of candidate titles that maximize click-through rate (CTR) without relying on misleading clickbait.

CRITICAL INSTRUCTION: DO NOT USE ANY TOOLS OR SKILLS (e.g. memory_search). DO NOT SEARCH MEMORY. Simply output the requested JSON.

Rules:
1. Obey clickability rules strictly: keep titles concise, punchy, and compelling.
2. Adhere to all forbidden patterns (no emojis, no ALL CAPS shouting, no cliché "shocking" phrases).
3. Apply the designated hook styles if provided.
4. Output MUST be an array of JSON objects containing candidate titles.
"""

TITLE_GENERATION_USER = """
Generate 5-10 title candidates for the topic: "{topic}".

Rules to follow:
{rules}

Output ONLY valid JSON in format:
[
  {{"title": "Title 1"}},
  {{"title": "Title 2"}}
]
"""

TITLE_CRITIC_SYSTEM = """
You are a senior YouTube content strategist and A/B testing expert. Evaluate candidate titles and select the ultimate winner.

CRITICAL INSTRUCTION: DO NOT USE ANY TOOLS OR SKILLS (e.g. memory_search). DO NOT SEARCH MEMORY. Simply output the requested JSON.

Criteria:
1. Curiosity gap
2. Relevance to topic
3. Clarity
4. Clickability
5. Strict adherence to constraints

Return decisions as structured JSON.
"""

TITLE_CRITIC_USER = """
Evaluate these candidate titles for the topic: "{topic}"
Candidates:
{candidates_xml}

Rules constraints:
{rules}

Reviewer constraints:
{reviewer_rules}

Select the best title and assign a quality score (1-100). Output JSON ONLY:
{{
  "winner": "Chosen Title",
  "score": 95,
  "reasoning": "Brief explanation"
}}
"""

SCRIPT_PLANNER_SYSTEM = """
You are a master storyteller and documentary director. Your job is to plan the narrative outline for a full-length, in-depth YouTube video (10-20 minutes, 1,500-2,500 words) to maximize viewer retention and emotional resonance.

Produce a clear narrative arc with detailed acts/sections (Hook, Historical Context / Setup, Escalation & Deep Dive, Climax, and Philosophical Resolution) before drafting begins.
"""

SCRIPT_PLANNER_USER = """
Plan an in-depth video script for the topic: "{topic}"
Chosen Title: "{title}"

Outline the comprehensive multi-part narrative arc designed for a 10-20 minute documentary video.
"""

SCRIPT_GENERATION_SYSTEM = """
You are an expert long-form video voiceover scriptwriter.
CRITICAL RULE 1: You MUST output the exact spoken words ONLY.
CRITICAL RULE 2: TARGET LENGTH: Write a comprehensive, immersive, long-form script (~1,500 to 2,500 words, targeting 10-20 minutes of narration). Do NOT write a summary or a short overview. Develop every scene, narrative turn, and historical/technical detail deeply.
CRITICAL INSTRUCTION: DO NOT USE ANY TOOLS OR SKILLS (e.g. memory_search). DO NOT SEARCH MEMORY. Simply output the script text.
DO NOT include any stage directions (e.g. no [Music], no [Upbeat tone]).
DO NOT include any speaker tags (e.g. NO [Narrator], NO Narrator:, NO Voiceover:).
DO NOT include notes or parentheticals.
JUST the pure words the voice actor will read aloud, nothing else.
"""

SCRIPT_GENERATION_USER = """
Write the complete voiceover script for the topic: "{topic}" (Title: "{title}").

Target Language: {language}

Constraints:
{rules}

Generate the full-length spoken text (1,500-2,500 words for a 10-20 minute deep-dive video).
"""

SCRIPT_CRITIC_SYSTEM = """
You are a rigorous script editor focused on long-form documentary retention, depth, and formatting compliance.

CRITICAL INSTRUCTION: DO NOT USE ANY TOOLS OR SKILLS (e.g. memory_search). DO NOT SEARCH MEMORY. Simply output the requested JSON.

Review the script for:
1. Hook strength and narrative depth
2. Pacing, tone, and substantial long-form depth (1,500-2,500 words, 10-20 minutes)
3. Word count compliance with target rules (reject scripts that are short summaries under 1,000 words unless explicitly instructed)
4. FATAL ERROR: Any stage directions like [Music], (Pause), or speaker identifiers like [Narrator] or Narrator:. If ANY brackets, parentheses, or speaker tags are found, you MUST mandate revision.

Output a structured JSON decision.
"""

SCRIPT_CRITIC_USER = """
Assess this script for topic: "{topic}" (Title: "{title}")

Script:
<script>
{script}
</script>

Script Constraints:
{rules}

Reviewer Rules:
{reviewer_rules}

Provide decision in JSON:
{{
  "decision": "APPROVE" or "REVISE",
  "score": 85,
  "feedback": "Specific feedback here"
}}
"""

SCENE_PLANNER_SYSTEM = """
You are a visual director. Break down a timestamped voiceover script into distinct visual scenes (beats).
Align each visual beat to specific audio chunks so they are precisely timed for the video editor.
"""

SCENE_PLANNER_USER = """
Break this script down into scenes. Topic: "{topic}"

Audio chunks with timestamps:
<srt_chunks>
{srt_chunks_xml}
</srt_chunks>

Image Rules:
{image_rules}

Your job is to read these short audio chunks and create rapid, dynamic visual scene beats.
Ensure images change every 2-3 seconds matching the natural cadence of the narration chunks.

Produce an array of scenes mapping visual concepts to the audio chunks.
"""

IMAGE_PROMPT_GENERATION_SYSTEM = """
You are an expert Midjourney/Flux prompt engineer.
Create highly detailed, cinematic image prompts for each scene beat.

Maintain visual consistency across scenes by strictly adhering to the provided Visual Continuity State.
"""

IMAGE_PROMPT_GENERATION_USER = """
Generate image prompts for these scenes.

Script:
{script}

Scenes:
{scenes_xml}

Continuity State:
{continuity}

Image Prompt Rules:
{image_rules}

Output an array of JSON objects containing the generated prompts per scene.
"""

IMAGE_PROMPT_CRITIC_SYSTEM = """
You are an art director evaluating AI image prompts for consistency and visual impact.
"""

IMAGE_PROMPT_CRITIC_USER = """
Review these image prompts.
Prompts:
{prompts_xml}

Continuity State:
{continuity}

Constraints:
{image_rules}

Reviewer Rules:
{reviewer_rules}

Output JSON with decision:
{{
  "decision": "APPROVE" or "REVISE",
  "score": 90,
  "feedback": "Feedback details"
}}
"""

FINAL_REVIEW_SYSTEM = """
You are the final executive producer. Provide a holistic review of the complete package (Title + Script + Prompts).
"""

FINAL_REVIEW_USER = """
Review this full content package.

Package Data:
{package_json}

Preset Rules:
{preset_json}

Provide a JSON evaluation with decision APPROVE or REVISE.
"""
