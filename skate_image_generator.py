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

Image API integration is supported through _call_image_api()
using Google Imagen via Vertex AI.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

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
    "toe spin":      "toe spin",
    "one foot spin": "one-foot spin",
    "spin":          "spin",
    "transition":    "transition",
    "t-stop":        "T-stop",
    "t stop":        "T-stop",
    "crossovers":    "crossovers",
    "crossover":     "crossovers",
    "toe manual":    "toe manual",
    "heel manual":   "heel manual",
    "manual":        "manual",
    "pivot":         "pivot",
    "backwards":     "backward skating",
    "backward":      "backward skating",
    "snapping":      "snapping",
    "snap":          "snapping",
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


# ─────────────────────────────────────────────
# TRIGGER DETECTION
# ─────────────────────────────────────────────

def should_trigger_generated_visual(user_message: str) -> bool:
    """
    Returns True ONLY when the user is explicitly asking for a generated
    visual output — technique diagram, step breakdown, setup visual, or
    corrected form.
    """
    lower = (user_message or "").lower().strip()

    youtube_exclusions = ["tutorial", "tutorials", "video", "videos", "youtube", "watch"]
    if any(excl in lower for excl in youtube_exclusions):
        return False

    visual_phrases = [
        "show me what",
        "show me how it looks",
        "show me how it should look",
        "show me proper",
        "show me correct",
        "what does it look like",
        "give me a visual",
        "generate an image",
        "show correct posture",
        "show me proper form",
        "show proper form",
        "show me a skate setup",
        "show me a setup",
        "visualize",
        "diagram",
        "step-by-step visual",
    ]

    breakdown_visual_phrases = [
        "show the steps",
        "break it down visually",
        "step by step visually",
        "show me step by step",
        "show me the steps",
    ]

    return any(phrase in lower for phrase in (visual_phrases + breakdown_visual_phrases))


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
    lower = (user_message or "").lower()

    if any(kw in lower for kw in _SETUP_KEYWORDS):
        return "setup"

    if any(p in lower for p in [
        "step by step visually",
        "step-by-step visual",
        "break it down visually",
        "show me the steps",
        "show the steps",
    ]):
        return "breakdown"

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

    return "technique"


def _extract_technique(user_message: str) -> str:
    """
    Pull the most relevant skating technique name from the message.
    Falls back to the raw message if no known keyword matches.
    """
    lower = (user_message or "").lower()

    # Prefer longer keywords first so "toe spin" wins over "spin"
    for keyword, label in sorted(_TECHNIQUE_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
        if keyword in lower:
            return label

    cleaned = lower
    for phrase in _VISUAL_TRIGGER_PHRASES:
        cleaned = cleaned.replace(phrase, "")

    cleaned = cleaned.strip(" .,!?:;-")
    return cleaned.title() or "Skating Technique"


def _extract_setup_style(user_message: str) -> str:
    """
    Pull the skating style from a setup request.
    """
    lower = (user_message or "").lower()
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
# IMAGE API — Google Imagen via Vertex AI
#
# SETUP REQUIREMENTS:
#   pip install google-cloud-aiplatform
#   gcloud auth application-default login
#   Enable Vertex AI API in Google Cloud Console
#
# Required environment variables (.env):
#   GOOGLE_CLOUD_PROJECT   — your GCP project ID
#   GOOGLE_CLOUD_LOCATION  — e.g. "us-central1"  (default if missing)
#   IMAGEN_MODEL           — e.g. "imagen-4.0-generate-001" (default if missing)
# ─────────────────────────────────────────────
def _call_image_api(prompt: str) -> Optional[str]:
    """
    Generate an image using Google Imagen via Vertex AI.

    Saves the result as a local temp .png file and returns the file path.
    Returns None if generation fails or env vars are not set.
    """
    try:
        import os
        import tempfile
        import vertexai
        from vertexai.preview.vision_models import ImageGenerationModel

        import streamlit as st

        project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT"))
        location = st.secrets.get("GOOGLE_CLOUD_LOCATION", os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
        model_name = st.secrets.get("IMAGEN_MODEL", os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001"))

        if not project_id:
            print("[Imagen Error] GOOGLE_CLOUD_PROJECT env var is not set.")
            return None

        vertexai.init(project=project_id, location=location)

        model = ImageGenerationModel.from_pretrained(model_name)
        result = model.generate_images(
            prompt=prompt,
            number_of_images=1,
        )

        if not getattr(result, "images", None):
            print("[Imagen Error] No images returned from Vertex AI.")
            return None

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        result.images[0].save(tmp.name)
        tmp.close()
        return tmp.name

    except Exception as exc:
        print(f"[Imagen Error] {exc}")
        return None


# ─────────────────────────────────────────────
# PROMPT BUILDERS
# ─────────────────────────────────────────────

def _build_technique_prompt(technique: str, skill_level: str) -> str:
    """Build a coaching-style image generation prompt for a skating technique."""
    level_note = {
        "Beginner": "simplified form, clearly visible basics, no advanced details",
        "Intermediate": "refined technique, good form, moderate detail",
        "Advanced": "precise professional technique, full detail, competition-ready form",
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
    step_templates = {
        "transition": [
            ("Setup", "Roll forward, feet parallel, knees soft, weight centered.",
             f"Quad roller skater rolling forward in neutral stance, knees bent, weight centered, arms relaxed. {skill_level} level."),
            ("Weight Shift", "Shift weight to your dominant foot before turning.",
             f"Quad roller skater shifting weight to left or right foot, slight lean, other foot lifting slightly. {skill_level} level."),
            ("The Turn", "Rotate hips and shoulders together as one unit.",
             f"Quad roller skater mid-transition, hips rotating, shoulders following, one foot pivoting. {skill_level} level."),
            ("Land Backward", "Find your balance rolling backward, knees still soft.",
             f"Quad roller skater rolling backward confidently, knees bent, weight centered, arms out for balance. {skill_level} level."),
        ],
        "T-stop": [
            ("Setup", "Roll forward at a comfortable speed, feet parallel.",
             f"Quad roller skater rolling forward, relaxed posture, moderate speed. {skill_level} level."),
            ("Rear Foot Position", "Bring your rear foot perpendicular to your direction of travel.",
             f"Quad roller skater with rear foot turning 90 degrees, beginning to drag. {skill_level} level."),
            ("Apply Pressure", "Press the inside edge of the rear wheels gently to the floor.",
             f"Quad roller skater applying controlled pressure with rear foot, slight friction visible. {skill_level} level."),
            ("Come to a Stop", "Hold the T position until fully stopped. Keep weight forward.",
             f"Quad roller skater fully stopped in T-stop position, front foot forward, rear foot perpendicular. {skill_level} level."),
        ],
        "crossovers": [
            ("Start Position", "Lean slightly into the curve, weight on the outside edge.",
             f"Quad roller skater leaning into a turn, weight on outside edges, arms extended. {skill_level} level."),
            ("Cross Over", "Lift the outside foot and cross it over the inside foot.",
             f"Quad roller skater crossing outside foot over inside foot mid-stride. {skill_level} level."),
            ("Plant & Push", "Plant the crossed foot and push outward with the inside foot.",
             f"Quad roller skater planting crossed foot, pushing off with inside foot for power. {skill_level} level."),
            ("Recover", "Bring feet back to parallel and repeat the cross.",
             f"Quad roller skater recovering to parallel position, flowing into the next crossover. {skill_level} level."),
        ],
        "backward skating": [
            ("Setup", "Face forward, then push off one foot to begin rolling backward.",
             f"Quad roller skater in starting position, about to initiate backward rolling. {skill_level} level."),
            ("C-Cut", "Use a C-shaped push with one foot to propel yourself backward.",
             f"Quad roller skater executing a C-cut stroke backward, one foot carving outward. {skill_level} level."),
            ("Balance Check", "Keep knees bent, chest up, and look over your shoulder.",
             f"Quad roller skater rolling backward with good posture, knees bent, looking back safely. {skill_level} level."),
            ("Build Speed", "Alternate C-cuts on each foot for consistent backward momentum.",
             f"Quad roller skater alternating C-cuts backward, gaining speed with controlled form. {skill_level} level."),
        ],
    }

    lower_technique = technique.lower()
    matched_steps = None
    for key, steps in step_templates.items():
        if key in lower_technique or lower_technique in key:
            matched_steps = steps
            break

    if not matched_steps:
        matched_steps = [
            ("Setup", f"Get into starting position for {technique}.",
             f"Quad roller skater in starting position preparing for {technique}. {skill_level} level."),
            ("Initiate", "Begin the movement with proper weight transfer.",
             f"Quad roller skater initiating {technique}, weight shifting, knees bent. {skill_level} level."),
            ("Execute", "Follow through the core motion with control.",
             f"Quad roller skater mid-execution of {technique}, full technique on display. {skill_level} level."),
            ("Finish", "Recover to a balanced, neutral stance.",
             f"Quad roller skater completing {technique}, landing balanced, knees soft. {skill_level} level."),
        ]

    return [
        {
            "step": i + 1,
            "title": title,
            "caption": caption,
            "image_prompt": prompt,
            "image_url": _call_image_api(prompt),
        }
        for i, (title, caption, prompt) in enumerate(matched_steps)
    ]


def _build_correction_prompt(coaching_summary: str, skill_level: str) -> str:
    """Build a corrected-form image prompt from Remy's coaching text."""
    summary = (coaching_summary or "")[:200]
    return (
        "A clear coaching illustration of a quad roller skater demonstrating correct form. "
        "The skater shows properly bent knees, upright chest, centered weight distribution, "
        "relaxed arms, stable ankle alignment, and confident balanced posture. "
        f"This corrected version addresses these coaching notes: '{summary}'. "
        f"Clean background, coaching diagram style, {skill_level} skill level context. "
        "No text overlays. High quality. Photorealistic or clean illustration."
    )


def _build_setup_prompt(style: str, skill_level: str) -> str:
    """Build a skate setup image prompt for a given skating style."""
    setup_details = {
        "Jam": "low-cut boot for ankle mobility, hard wheels (95A-101A), loose trucks, small toe stop",
        "Rhythm": "mid-cut boot, medium-hard wheels (88A-95A), standard plate, standard toe stop",
        "Outdoor": "high-cut boot for ankle support, soft outdoor wheels (76A-85A), loose trucks, no toe stop or small plug",
        "Artistic": "high-cut stiff boot, hard precision wheels, tight trucks, large toe stop",
        "Derby": "low-cut boot, medium-hard wheels, wide plate, small plug instead of a toe stop",
        "Park": "low-cut boot, hard wheels (97A-101A), loose trucks, small plug or no toe stop",
        "Speed": "low-cut speed boot, hard wheels (98A-101A), long plate, no toe stop",
        "Street": "mid-cut boot, hard wheels (95A-101A), wide plate, small toe stop",
        "Freestyle": "low or mid-cut boot, medium-hard wheels (88A-95A), standard plate",
        "Beginner": "mid-cut supportive boot, medium wheels (82A-88A), standard plate, standard toe stop",
        "General": "all-purpose quad skate with medium-hardness wheels and standard setup",
    }
    detail = setup_details.get(style, setup_details["General"])

    return (
        f"A detailed product-style illustration of a complete {style} roller skate setup. "
        f"Setup specs: {detail}. "
        "Show both skates from a 3/4 angle, clearly displaying the boot, plate, wheels, and toe stop. "
        "Clean white background, product photography style, high detail. "
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
    """
    try:
        technique = _extract_technique(user_message)
        image_prompt = _build_technique_prompt(technique, skill_level)
        image_url = _call_image_api(image_prompt)

        return {
            "success": True,
            "type": "technique_visual",
            "title": f"{technique} — Technique Visual",
            "description": f"A coaching-style visual showing correct {technique} posture, foot placement, and balance.",
            "image_prompt": image_prompt,
            "image_url": image_url,
            "steps": [],
        }
    except Exception as exc:
        return _error_result("technique_visual", str(exc))


def generate_trick_breakdown_visuals(
    user_message: str,
    skill_level: str = "Intermediate",
) -> dict:
    """
    Generate a step-by-step visual breakdown for a skating move.
    """
    try:
        technique = _extract_technique(user_message)
        steps = _build_step_prompts(technique, skill_level)

        return {
            "success": True,
            "type": "trick_breakdown",
            "title": f"{technique} — Step-by-Step Breakdown",
            "description": f"A {len(steps)}-step visual breakdown of {technique} for a {skill_level} skater.",
            "image_prompt": None,
            "image_url": None,
            "steps": steps,
        }
    except Exception as exc:
        return _error_result("trick_breakdown", str(exc))


def generate_corrected_form_visual(
    coaching_summary: str,
    skill_level: str = "Intermediate",
) -> dict:
    """
    Generate a corrected-form visual from Remy's coaching text.
    """
    try:
        if not coaching_summary or not coaching_summary.strip():
            return _error_result("corrected_form", "No coaching summary provided.")

        image_prompt = _build_correction_prompt(coaching_summary, skill_level)
        image_url = _call_image_api(image_prompt)

        return {
            "success": True,
            "type": "corrected_form",
            "title": "Corrected Form Visual",
            "description": "A visual showing what correct skating form looks like based on Remy's coaching notes.",
            "image_prompt": image_prompt,
            "image_url": image_url,
            "steps": [],
        }
    except Exception as exc:
        return _error_result("corrected_form", str(exc))


def generate_skate_setup_visual(
    user_message: str,
    skill_level: str = "Intermediate",
) -> dict:
    """
    Generate a visual for a skate setup based on skating style.
    """
    try:
        style = _extract_setup_style(user_message)
        image_prompt = _build_setup_prompt(style, skill_level)
        image_url = _call_image_api(image_prompt)

        return {
            "success": True,
            "type": "setup_visual",
            "title": f"{style} Skating Setup",
            "description": f"A visual breakdown of a recommended {style} quad skate setup for a {skill_level} skater.",
            "image_prompt": image_prompt,
            "image_url": image_url,
            "steps": [],
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
    """
    visual_type = _detect_visual_type(user_message)

    if visual_type == "setup":
        return generate_skate_setup_visual(user_message, skill_level)
    if visual_type == "breakdown":
        return generate_trick_breakdown_visuals(user_message, skill_level)
    if visual_type == "correction" and coaching_summary:
        return generate_corrected_form_visual(coaching_summary, skill_level)
    return generate_technique_visual(user_message, skill_level)


# ─────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────

def _error_result(visual_type: str, error_msg: str) -> dict:
    """Return a structured error result that won't crash the caller."""
    return {
        "success": False,
        "type": visual_type,
        "title": "Visual Unavailable",
        "description": f"Could not generate visual: {error_msg}",
        "image_prompt": None,
        "image_url": None,
        "steps": [],
        "error": error_msg,
    }


# ─────────────────────────────────────────────
# STREAMLIT RENDERER
# ─────────────────────────────────────────────

def render_generated_visual(visual_result: dict) -> None:
    """
    Render a generated visual result inside a Streamlit context.

    Call this INSIDE your st.chat_message("assistant") block,
    AFTER placeholder.markdown(clean_text) and AFTER render_rich_cards().
    """
    try:
        import streamlit as st
    except ImportError:
        print("[skate_image_generator] Streamlit not available — skipping render.")
        return

    if not visual_result or not visual_result.get("success"):
        return

    title = visual_result.get("title", "Visual")
    desc = visual_result.get("description", "")
    url = visual_result.get("image_url")
    steps = visual_result.get("steps", [])

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

    if url:
        st.image(url, use_container_width=True)
    else:
        prompt = visual_result.get("image_prompt", "")
        if prompt:
            st.markdown(
                f"<div style='background:#101828; border:1px dashed #1a2840; "
                f"border-radius:10px; padding:12px 15px; font-size:0.78rem; "
                f"color:#6a85a8; margin-bottom:8px;'>"
                f"<strong style='color:#c6ff4a;'>📐 Image Prompt (connect an image API to generate)</strong><br>"
                f"<em>{prompt[:300]}{'…' if len(prompt) > 300 else ''}</em></div>",
                unsafe_allow_html=True,
            )

    if steps:
        for step in steps:
            n = step.get("step", "")
            stitle = step.get("title", "")
            caption = step.get("caption", "")
            sprompt = step.get("image_prompt", "")
            surl = step.get("image_url")

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