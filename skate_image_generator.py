"""
skate_image_generator.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Modular visual coaching extension for Coach Remy.

This module generates structured coaching visuals — technique
descriptions, step-by-step trick breakdowns, corrected-form
prompts, and skate setup visuals — based on user messages.

It is COMPLETELY SEPARATE from the main chatbot. It does not
touch, replace, or duplicate:
  - Gemini chat / streaming
  - YouTube search
  - Google CSE product image search
  - Trusted-source search
  - Photo/video upload or frame extraction
  - Streamlit UI or CSS
  - extract_tags / render_rich_cards

It only adds generated visual coaching results that appear
BELOW Remy's normal coaching text when triggered.

Image API integration is stubbed (image_url returns None).
Drop in any image generation API (Imagen, DALL·E, Stability AI)
by implementing _call_image_api() at the bottom of this file.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
from typing import Optional


# ─────────────────────────────────────────────
# CONSTANTS — trigger keywords and known moves
# ─────────────────────────────────────────────

# Legacy constant kept for reference — trigger logic now lives in
# should_trigger_generated_visual() using two stricter phrase groups.
# Do not use this list directly; call should_trigger_generated_visual() instead.
_VISUAL_TRIGGER_PHRASES = [
    "show me",
    "what does it look like",
    "what does a",
    "what does the",
    "what should a",
    "give me a visual",
    "break it down visually",
    "generate an image",
    "show correct posture",
    "show me proper form",
    "show proper form",
    "what should this look like",
    "what should it look like",
    "show me a skate setup",
    "visualize",
    "can you show",
    "diagram",
    "show the steps",
    "step-by-step visual",
]

# Known skating techniques that map to rich visual descriptions
_TECHNIQUE_KEYWORDS = {
    "spin":          "spin",
    "toe spin":      "toe spin",
    "one foot spin": "one-foot spin",
    "transition":    "transition",
    "t-stop":        "T-stop",
    "t stop":        "T-stop",
    "crossover":     "crossovers",
    "crossovers":    "crossovers",
    "manual":        "manual",
    "toe manual":    "toe manual",
    "heel manual":   "heel manual",
    "pivot":         "pivot",
    "backward":      "backward skating",
    "backwards":     "backward skating",
    "snap":          "snapping",
    "snapping":      "snapping",
    "shuffle":       "shuffle",
    "jb":            "JB skating",
    "jam":           "jam skating",
    "rhythm":        "rhythm skating",
    "derby":         "roller derby",
    "hockey":        "roller hockey",
    "jump":          "jump",
    "mohawk":        "mohawk turn",
    "three turn":    "three turn",
    "lunge":         "lunge stop",
}

# Skate setup styles
_SETUP_KEYWORDS = [
    "jam skating setup",
    "jam setup",
    "rhythm setup",
    "rhythm skating setup",
    "outdoor setup",
    "trail setup",
    "artistic setup",
    "derby setup",
    "park setup",
    "speed setup",
    "street setup",
    "freestyle setup",
    "slalom setup",
    "beginner setup",
    "setup for",
    "skate setup",
    "what skates",
    "recommend a setup",
    "setup recommendation",
]

# Correction cues that suggest a corrected-form visual would help
_CORRECTION_KEYWORDS = [
    "knees",
    "posture",
    "stance",
    "weight",
    "chest",
    "back",
    "arms",
    "balance",
    "lean",
    "hip",
    "core",
    "foot placement",
    "ankle",
    "upright",
    "bend",
    "form",
]


# ─────────────────────────────────────────────
# TRIGGER DETECTION
# ─────────────────────────────────────────────

def should_trigger_generated_visual(user_message: str) -> bool:
    """
    Returns True ONLY when the user is explicitly asking for a generated
    visual output — technique diagram, step breakdown, setup visual, or
    corrected form.
    """
    lower = user_message.lower().strip()

    youtube_exclusions = ["tutorial", "tutorials", "video", "videos", "youtube", "watch"]
    if any(excl in lower for excl in youtube_exclusions):
        return False

    visual_phrases = [
        # explicit show/show me phrases
        "show me what",
        "show me how it looks",
        "show me how it should look",
        "show me proper",
        "show me correct",
        "show me the visual",
        "show me a visual",
        "show me an image",
        "show me a picture",
        # create / make / generate
        "create the visual",
        "create a visual",
        "create an image",
        "make a visual",
        "make an image",
        "generate a visual",
        "generate an image",
        "generate the visual",
        # give / send
        "give me a visual",
        "give me an image",
        "give me a picture",
        "send me a visual",
        # can you
        "can you create",
        "can you generate",
        "can you make",
        "can you show me",
        # posture / form
        "show correct posture",
        "show me proper form",
        "show proper form",
        # setup
        "show me a skate setup",
        "show me a setup",
        # misc
        "what does it look like",
        "visualize",
        "diagram",
        "step-by-step visual",
        "i want to see",
        "let me see",
    ]

    breakdown_visual_phrases = [
        "show the steps",
        "break it down visually",
        "step by step visually",
        "show me step by step",
        "show me the steps",
    ]

    return any(phrase in lower for phrase in visual_phrases + breakdown_visual_phrases)


def _detect_visual_type(user_message: str) -> str:
    """
    Classify which type of visual the user is asking for.

    Returns one of:
    - "technique"   → single move / posture visualization
    - "breakdown"   → step-by-step trick breakdown
    - "correction"  → corrected form from coaching text
    - "setup"       → skate setup for a style
    - "technique"   → default fallback
    """
    lower = user_message.lower()

    # Setup check first — most specific
    if any(kw in lower for kw in _SETUP_KEYWORDS):
        return "setup"

    # Step-by-step signals
    if any(p in lower for p in [
        "step by step visually",
        "step-by-step visual",
        "break it down visually",
        "show me the steps",
        "show the steps",
    ]):
        return "breakdown"

    # Corrected form signals — only explicit visual correction requests.
    # "fix my form" alone stays as normal coaching, not a visual trigger.
    correction_phrases = [
        "show me corrected form",
        "show corrected form",
        "show what my form should look like",
        "show what proper form looks like",
        "visualize the correction",
        "show the corrected posture",
        "show me the correction",
        "show corrected posture",
    ]
    if any(p in lower for p in correction_phrases):
        return "correction"

    # Default: technique visual
    return "technique"


def _extract_technique(user_message: str) -> str:
    """
    Pull the most relevant skating technique name from the message.
    Falls back to the raw message if no known keyword matches.
    """
    lower = user_message.lower()
    for keyword, label in _TECHNIQUE_KEYWORDS.items():
        if keyword in lower:
            return label
    # Fallback — strip trigger phrases and use whatever's left
    cleaned = lower
    for phrase in _VISUAL_TRIGGER_PHRASES:
        cleaned = cleaned.replace(phrase, "")
    return cleaned.strip().title() or "Skating Technique"


def _extract_setup_style(user_message: str) -> str:
    """
    Pull the skating style from a setup request.
    """
    lower = user_message.lower()
    styles = [
        "jam", "rhythm", "outdoor", "trail", "artistic",
        "derby", "park", "speed", "street", "freestyle",
        "slalom", "beginner",
    ]
    for style in styles:
        if style in lower:
            return style.title()
    return "General"


# ─────────────────────────────────────────────
# IMAGE API — OpenAI DALL·E 3
#
# SETUP REQUIREMENTS:
#   pip install openai requests
#
# Required environment variables (.env):
#   OPENAI_API_KEY  — your OpenAI API key
#
# Optional:
#   DALLE_MODEL     — defaults to "dall-e-3"
#   DALLE_SIZE      — defaults to "1024x1024"
#                     options: "1024x1024" | "1792x1024" | "1024x1792"
#   DALLE_QUALITY   — defaults to "standard"  ("hd" for higher quality, costs more)
# ─────────────────────────────────────────────
def _call_image_api(prompt: str) -> Optional[str]:
    """
    Generate an image using OpenAI DALL·E 3.

    Downloads the result and saves it as a local temp .png file.
    Returns the file path on success, None on any failure.
    Never raises — all errors are printed for terminal debugging.

    Parameters
    ----------
    prompt : str
        The image generation prompt.

    Returns
    -------
    str or None
        Local file path to the generated .png, or None on failure.
    """
    import os
    import tempfile
    import requests as _requests

    # ── Step 1: env var check (st.secrets first for Streamlit Cloud, then .env) ──
    try:
        import streamlit as _st
        api_key = _st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        model   = _st.secrets.get("DALLE_MODEL")    or os.getenv("DALLE_MODEL",   "dall-e-3")
        size    = _st.secrets.get("DALLE_SIZE")     or os.getenv("DALLE_SIZE",    "1024x1024")
        quality = _st.secrets.get("DALLE_QUALITY")  or os.getenv("DALLE_QUALITY", "standard")
    except Exception:
        api_key = os.getenv("OPENAI_API_KEY")
        model   = os.getenv("DALLE_MODEL",   "dall-e-3")
        size    = os.getenv("DALLE_SIZE",    "1024x1024")
        quality = os.getenv("DALLE_QUALITY", "standard")

    if not api_key:
        print(
            "[DALL·E] FAIL — OPENAI_API_KEY not found in st.secrets or .env. "
            "Add it to your Streamlit Cloud secrets or .env file."
        )
        return None

    print(f"[DALL·E] Generating — model={model!r} size={size!r} quality={quality!r}")

    # ── Step 2: import openai ──
    try:
        import openai
    except ImportError:
        print(
            "[DALL·E] FAIL — openai package not installed. "
            "Run: pip install openai"
        )
        return None

    # ── Step 3: call DALL·E API ──
    try:
        client   = openai.OpenAI(api_key=api_key)
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            size=size,
            quality=quality,
            response_format="url",
        )
        image_url = response.data[0].url
    except openai.AuthenticationError as exc:
        print(f"[DALL·E] FAIL — Invalid API key. Check OPENAI_API_KEY in your .env. ({exc})")
        return None
    except openai.RateLimitError as exc:
        print(f"[DALL·E] FAIL — Rate limit or quota exceeded. ({exc})")
        return None
    except openai.BadRequestError as exc:
        print(f"[DALL·E] FAIL — Prompt was rejected (likely content policy). ({exc})")
        return None
    except Exception as exc:
        print(f"[DALL·E] FAIL — API error ({type(exc).__name__}): {exc}")
        return None

    # ── Step 4: download image to temp file ──
    try:
        img_data = _requests.get(image_url, timeout=30).content
        tmp      = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(img_data)
        tmp.close()
        print(f"[DALL·E] OK — image saved to {tmp.name!r}")
        return tmp.name
    except Exception as exc:
        print(f"[DALL·E] FAIL — could not download/save image ({type(exc).__name__}): {exc}")
        return None


# ─────────────────────────────────────────────
# PROMPT BUILDERS
# ─────────────────────────────────────────────

def _build_technique_prompt(technique: str, skill_level: str) -> str:
    """Build a coaching-style image generation prompt for a skating technique."""
    level_note = {
        "Beginner":     "simplified form, clearly visible basics, no advanced details",
        "Intermediate": "refined technique, good form, moderate detail",
        "Advanced":     "precise professional technique, full detail, competition-ready form",
    }.get(skill_level, "moderate detail")

    return (
        f"A clear coaching diagram of a quad roller skater demonstrating proper {technique} technique. "
        f"Shown from a 3/4 angle to display both feet and upper body. "
        f"Body posture is correct: knees bent, weight centered, arms relaxed at sides. "
        f"Foot placement is clearly visible on the floor. "
        f"Motion direction indicated by subtle arrows or body angle. "
        f"Clean white or rink-blue background. Coaching illustration style. "
        f"Skill level context: {level_note}. "
        f"No text overlays. Photorealistic or clean illustration. High quality."
    )


def _build_step_prompts(technique: str, skill_level: str) -> list:
    """
    Build a list of step-by-step image prompts for a skating move.
    Returns a list of step dicts ready for the output format.
    """
    # Step templates keyed by technique keyword
    step_templates = {
        "transition": [
            ("Setup",         "Roll forward, feet parallel, knees soft, weight centered.",
             f"Quad roller skater rolling forward in neutral stance, knees bent, weight centered, arms relaxed. {skill_level} level."),
            ("Weight Shift",  "Shift weight to your dominant foot before turning.",
             f"Quad roller skater shifting weight to left/right foot, slight lean, other foot lifting slightly. {skill_level} level."),
            ("The Turn",      "Rotate hips and shoulders together as one unit.",
             f"Quad roller skater mid-transition, hips rotating, shoulders following, one foot pivoting on toe stop. {skill_level} level."),
            ("Land Backward", "Find your balance rolling backward, knees still soft.",
             f"Quad roller skater rolling backward confidently, knees bent, weight centered, arms out for balance. {skill_level} level."),
        ],
        "T-stop": [
            ("Setup",         "Roll forward at a comfortable speed, feet parallel.",
             f"Quad roller skater rolling forward, relaxed posture, moderate speed. {skill_level} level."),
            ("Rear Foot Position", "Bring your rear foot perpendicular to your direction of travel.",
             f"Quad roller skater with rear foot turning 90 degrees, beginning to drag. {skill_level} level."),
            ("Apply Pressure", "Press the inside edge of the rear wheels gently to the floor.",
             f"Quad roller skater applying controlled pressure with rear foot, slight friction visible. {skill_level} level."),
            ("Come to a Stop", "Hold the T position until fully stopped. Keep weight forward.",
             f"Quad roller skater fully stopped in T-stop position, front foot forward, rear foot perpendicular. {skill_level} level."),
        ],
        "crossovers": [
            ("Start Position", "Lean slightly into the curve, weight on outside edge.",
             f"Quad roller skater leaning into a turn, weight on outside edges, arms extended. {skill_level} level."),
            ("Cross Over",    "Lift the outside foot and cross it over the inside foot.",
             f"Quad roller skater crossing outside foot over inside foot mid-stride. {skill_level} level."),
            ("Plant & Push",  "Plant the crossed foot and push outward with the inside foot.",
             f"Quad roller skater planting crossed foot, pushing off with inside foot for power. {skill_level} level."),
            ("Recover",       "Bring feet back to parallel and repeat the cross.",
             f"Quad roller skater recovering to parallel position, flowing into the next crossover. {skill_level} level."),
        ],
        "backward skating": [
            ("Setup",         "Face forward, then push off one foot to begin rolling backward.",
             f"Quad roller skater in starting position, about to initiate backward rolling. {skill_level} level."),
            ("C-Cut",         "Use a C-shaped push with one foot to propel yourself backward.",
             f"Quad roller skater executing a C-cut stroke backward, one foot carving outward. {skill_level} level."),
            ("Balance Check", "Keep knees bent, chest up, and look over your shoulder.",
             f"Quad roller skater rolling backward with good posture, knees bent, looking back safely. {skill_level} level."),
            ("Build Speed",   "Alternate C-cuts on each foot for consistent backward momentum.",
             f"Quad roller skater alternating C-cuts backward, gaining speed with controlled form. {skill_level} level."),
        ],
    }

    # Find best matching template
    lower_technique = technique.lower()
    matched_steps = None
    for key, steps in step_templates.items():
        if key in lower_technique or lower_technique in key:
            matched_steps = steps
            break

    # Generic fallback steps
    if not matched_steps:
        matched_steps = [
            ("Setup",        f"Get into starting position for {technique}.",
             f"Quad roller skater in starting position preparing for {technique}. {skill_level} level."),
            ("Initiate",     f"Begin the movement with proper weight transfer.",
             f"Quad roller skater initiating {technique}, weight shifting, knees bent. {skill_level} level."),
            ("Execute",      f"Follow through the core motion with control.",
             f"Quad roller skater mid-execution of {technique}, full technique on display. {skill_level} level."),
            ("Finish",       f"Recover to a balanced, neutral stance.",
             f"Quad roller skater completing {technique}, landing balanced, knees soft. {skill_level} level."),
        ]

    return [
        {
            "step":         i + 1,
            "title":        title,
            "caption":      caption,
            "image_prompt": prompt,
            "image_url":    _call_image_api(prompt),
        }
        for i, (title, caption, prompt) in enumerate(matched_steps)
    ]


def _build_correction_prompt(coaching_summary: str, skill_level: str) -> str:
    """Build a corrected-form image prompt from Remy's coaching text."""
    return (
        f"A clear coaching illustration of a quad roller skater demonstrating CORRECT form. "
        f"The skater shows: properly bent knees, upright chest, centered weight distribution, "
        f"relaxed arms, stable ankle alignment, and confident balanced posture. "
        f"This is the corrected version addressing these coaching notes: '{coaching_summary[:200]}'. "
        f"Clean background, coaching diagram style, {skill_level} skill level context. "
        f"No text overlays. High quality. Photorealistic or clean illustration."
    )


def _build_setup_prompt(style: str, skill_level: str) -> str:
    """Build a skate setup image prompt for a given skating style."""
    setup_details = {
        "Jam":       "low-cut boot for ankle mobility, hard wheels (95A-101A), loose trucks, small toe stop",
        "Rhythm":    "mid-cut boot, medium-hard wheels (88A-95A), standard plate, standard toe stop",
        "Outdoor":   "high-cut boot for ankle support, soft outdoor wheels (76A-85A), loose trucks, no toe stop or small plug",
        "Artistic":  "high-cut stiff boot, hard precision wheels, tight trucks, large toe stop",
        "Derby":     "low-cut boot, outdoor-style wheels (88A), wide plate, no toe stop (small plug)",
        "Park":      "low-cut boot, hard wheels (97A-101A), loose trucks, no toe stop",
        "Speed":     "low-cut speed boot, hard wheels (98A-101A), long plate, no toe stop",
        "Street":    "mid-cut boot, hard wheels (95A-101A), wide plate, small toe stop",
        "Freestyle": "low or mid-cut boot, medium-hard wheels (88A-95A), standard plate",
        "Beginner":  "mid-cut supportive boot, medium wheels (82A-88A), standard plate, standard toe stop",
        "General":   "all-purpose quad skate with medium-hardness wheels and standard setup",
    }
    detail = setup_details.get(style, setup_details["General"])

    return (
        f"A detailed product-style illustration of a complete {style} roller skate setup. "
        f"Setup specs: {detail}. "
        f"Show both skates from a 3/4 angle, clearly displaying the boot, plate, wheels, and toe stop. "
        f"Clean white background, product photography style, high detail. "
        f"Label key components if possible. {skill_level} skater context."
    )


# ─────────────────────────────────────────────
# PUBLIC API — main functions
# ─────────────────────────────────────────────

def generate_technique_visual(
    user_message: str,
    skill_level: str = "Intermediate",
) -> dict:
    """
    Generate a coaching visual for a single skating technique.

    Parameters
    ----------
    user_message : str
        The user's message (e.g. "show me proper backward skating form").
    skill_level : str
        "Beginner", "Intermediate", or "Advanced".

    Returns
    -------
    dict
        Structured result with title, description, image_prompt, image_url.
    """
    try:
        technique    = _extract_technique(user_message)
        image_prompt = _build_technique_prompt(technique, skill_level)
        image_url    = _call_image_api(image_prompt)

        if image_url is None:
            return _error_result(
                "technique_visual",
                "Image generation failed — check terminal logs for details "
                "(missing GOOGLE_CLOUD_PROJECT, auth error, or Vertex API exception).",
            )

        return {
            "success":      True,
            "type":         "technique_visual",
            "title":        f"{technique} — Technique Visual",
            "description":  f"A coaching-style visual showing correct {technique} posture, foot placement, and balance.",
            "image_prompt": image_prompt,
            "image_url":    image_url,
            "steps":        [],
        }
    except Exception as exc:
        return _error_result("technique_visual", str(exc))


def generate_trick_breakdown_visuals(
    user_message: str,
    skill_level: str = "Intermediate",
) -> dict:
    """
    Generate a step-by-step visual breakdown for a skating move.

    Parameters
    ----------
    user_message : str
        The user's message (e.g. "break down the transition step by step visually").
    skill_level : str
        "Beginner", "Intermediate", or "Advanced".

    Returns
    -------
    dict
        Structured result with a list of steps, each containing
        title, caption, image_prompt, and image_url.
    """
    try:
        technique = _extract_technique(user_message)
        steps     = _build_step_prompts(technique, skill_level)

        return {
            "success":      True,
            "type":         "trick_breakdown",
            "title":        f"{technique} — Step-by-Step Breakdown",
            "description":  f"A {len(steps)}-step visual breakdown of {technique} for a {skill_level} skater.",
            "image_prompt": None,
            "image_url":    None,
            "steps":        steps,
        }
    except Exception as exc:
        return _error_result("trick_breakdown", str(exc))


def generate_corrected_form_visual(
    coaching_summary: str,
    skill_level: str = "Intermediate",
) -> dict:
    """
    Generate a corrected-form visual from Remy's coaching text.

    This is an ENHANCEMENT LAYER only. It does not replace or
    duplicate the main app's photo/video analysis via Gemini.
    It takes the text coaching output and visualises what correct
    form should look like based on those corrections.

    Parameters
    ----------
    coaching_summary : str
        Text from Remy's coaching response describing corrections
        (e.g. "knees need to bend more, chest should stay upright").
    skill_level : str
        "Beginner", "Intermediate", or "Advanced".

    Returns
    -------
    dict
        Structured result with a corrected-form image prompt.
    """
    try:
        if not coaching_summary or not coaching_summary.strip():
            return _error_result("corrected_form", "No coaching summary provided.")

        image_prompt = _build_correction_prompt(coaching_summary, skill_level)
        image_url    = _call_image_api(image_prompt)

        if image_url is None:
            return _error_result(
                "corrected_form",
                "Image generation failed — check terminal logs for details "
                "(missing GOOGLE_CLOUD_PROJECT, auth error, or Vertex API exception).",
            )

        return {
            "success":      True,
            "type":         "corrected_form",
            "title":        "Corrected Form Visual",
            "description":  "A visual showing what correct skating form looks like based on Remy's coaching notes.",
            "image_prompt": image_prompt,
            "image_url":    image_url,
            "steps":        [],
        }
    except Exception as exc:
        return _error_result("corrected_form", str(exc))


def generate_skate_setup_visual(
    user_message: str,
    skill_level: str = "Intermediate",
) -> dict:
    """
    Generate a visual for a skate setup based on skating style.

    Parameters
    ----------
    user_message : str
        The user's message (e.g. "show me a jam skating setup").
    skill_level : str
        "Beginner", "Intermediate", or "Advanced".

    Returns
    -------
    dict
        Structured result with setup description and image prompt.
    """
    try:
        style        = _extract_setup_style(user_message)
        image_prompt = _build_setup_prompt(style, skill_level)
        image_url    = _call_image_api(image_prompt)

        if image_url is None:
            return _error_result(
                "setup_visual",
                "Image generation failed — check terminal logs for details "
                "(missing GOOGLE_CLOUD_PROJECT, auth error, or Vertex API exception).",
            )

        return {
            "success":      True,
            "type":         "setup_visual",
            "title":        f"{style} Skating Setup",
            "description":  f"A visual breakdown of a recommended {style} quad skate setup for a {skill_level} skater.",
            "image_prompt": image_prompt,
            "image_url":    image_url,
            "steps":        [],
        }
    except Exception as exc:
        return _error_result("setup_visual", str(exc))


def generate_visual(
    user_message: str,
    skill_level: str = "Intermediate",
    coaching_summary: str = "",
) -> dict:
    """
    Master dispatcher — detects which visual type to generate and
    calls the appropriate function automatically.

    Use this as the single entry point from your main app.

    Parameters
    ----------
    user_message : str
        The raw user message.
    skill_level : str
        "Beginner", "Intermediate", or "Advanced".
    coaching_summary : str
        Optional — pass Remy's response text to enable corrected-form
        visuals when the user asks for correction-related visuals.

    Returns
    -------
    dict
        Structured visual result from the appropriate generator.
    """
    visual_type = _detect_visual_type(user_message)

    if visual_type == "setup":
        return generate_skate_setup_visual(user_message, skill_level)
    elif visual_type == "breakdown":
        return generate_trick_breakdown_visuals(user_message, skill_level)
    elif visual_type == "correction" and coaching_summary:
        return generate_corrected_form_visual(coaching_summary, skill_level)
    else:
        return generate_technique_visual(user_message, skill_level)


# ─────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────

def _error_result(visual_type: str, error_msg: str) -> dict:
    """Return a structured error result that won't crash the caller."""
    return {
        "success":      False,
        "type":         visual_type,
        "title":        "Visual Unavailable",
        "description":  f"Could not generate visual: {error_msg}",
        "image_prompt": None,
        "image_url":    None,
        "steps":        [],
        "error":        error_msg,
    }


# ─────────────────────────────────────────────
# STREAMLIT RENDERER
# ─────────────────────────────────────────────

def render_generated_visual(visual_result: dict) -> None:
    """
    Render a generated visual result inside a Streamlit context.

    Call this INSIDE your st.chat_message("assistant") block,
    AFTER placeholder.markdown(clean_text) and AFTER render_rich_cards().

    It uses only standard Streamlit markdown — no new CSS required.

    Parameters
    ----------
    visual_result : dict
        The dict returned by any generate_* function.
    """
    try:
        import streamlit as st
    except ImportError:
        print("[skate_image_generator] Streamlit not available — skipping render.")
        return

    if not visual_result:
        return

    if not visual_result.get("success"):
        # Show the failure reason so the user knows generation was attempted
        # but did not produce an image — not a silent no-op.
        err = visual_result.get("error", "Unknown error.")
        st.error(
            f"🎨 Visual generation failed — {err}",
            icon="⚠️",
        )
        return

    title = visual_result.get("title", "Visual")
    desc  = visual_result.get("description", "")
    url   = visual_result.get("image_url")
    steps = visual_result.get("steps", [])

    # Section divider
    st.markdown(
        "<div style='border-top:1px solid #1a2840; margin:16px 0 10px;'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:0.69rem; text-transform:uppercase; "
        f"letter-spacing:0.1em; color:#6a85a8; margin-bottom:8px;'>"
        f"🎨 Visual Coaching · {title}</div>",
        unsafe_allow_html=True,
    )

    if desc:
        st.markdown(
            f"<div style='font-size:0.82rem; color:#7a90b0; margin-bottom:10px;'>"
            f"{desc}</div>",
            unsafe_allow_html=True,
        )

    # Show generated image if available
    if url:
        st.image(url, use_container_width=True)
    else:
        # No image API yet — show the prompt so it's useful during dev
        prompt = visual_result.get("image_prompt", "")
        if prompt:
            st.markdown(
                f"<div style='background:#101828; border:1px dashed #c6ff4a44; "
                f"border-radius:12px; padding:16px 18px; margin-bottom:10px;'>"
                f"<div style='font-size:0.72rem; text-transform:uppercase; "
                f"letter-spacing:0.08em; color:#c6ff4a; margin-bottom:8px;'>"
                f"⚠️ Image API not connected — visual prompt ready</div>"
                f"<div style='font-size:0.85rem; color:#eef4ff; line-height:1.6;'>"
                f"{prompt[:500]}{'…' if len(prompt) > 500 else ''}</div>"
                f"<div style='font-size:0.72rem; color:#6a85a8; margin-top:10px;'>"
                f"Add OPENAI_API_KEY to your Streamlit secrets to generate this image.</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Step-by-step breakdown
    if steps:
        for step in steps:
            n       = step.get("step", "")
            stitle  = step.get("title", "")
            caption = step.get("caption", "")
            sprompt = step.get("image_prompt", "")
            surl    = step.get("image_url")

            st.markdown(
                f"<div style='background:#0c1220; border:1px solid #1a2840; "
                f"border-radius:10px; padding:11px 14px; margin:6px 0;'>"
                f"<div style='font-size:0.8rem; font-weight:600; color:#eef4ff;'>"
                f"Step {n} — {stitle}</div>"
                f"<div style='font-size:0.76rem; color:#7a90b0; margin-top:3px;'>"
                f"{caption}</div></div>",
                unsafe_allow_html=True,
            )
            if surl:
                st.image(surl, use_container_width=True)
            elif sprompt:
                st.markdown(
                    f"<div style='font-size:0.72rem; color:#4a6080; "
                    f"padding: 4px 14px; font-style:italic;'>"
                    f"↳ {sprompt[:200]}{'…' if len(sprompt) > 200 else ''}</div>",
                    unsafe_allow_html=True,
                )

    st.markdown(
        "<div style='border-top:1px solid #1a2840; margin:14px 0 4px;'></div>",
        unsafe_allow_html=True,
    )