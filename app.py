import os
import re
import html
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import requests
import google.generativeai as genai
from dotenv import load_dotenv
import streamlit as st
from PIL import Image
import io
import tempfile
import cv2
from skate_image_generator import (
    should_trigger_generated_visual,
    generate_visual,
    render_generated_visual,
)

# =========================
# 🔥 PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Coach Remy — Roller Skating AI",
    page_icon="🛼",
    layout="wide"
)

# =========================
# 🎨 CUSTOM CSS  (design unchanged)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

:root {
    --rink-dark:    #07090f;
    --rink-panel:   #0c1220;
    --rink-card:    #101828;
    --neon-lime:    #c6ff4a;
    --neon-cyan:    #3cf0ff;
    --neon-amber:   #ffb830;
    --user-bubble:  #0f2d5e;
    --bot-bubble:   #080f1e;
    --text-primary: #eef4ff;
    --text-muted:   #6a85a8;
    --border-dim:   #1a2840;
    --border-glow:  rgba(198,255,74,0.3);
    --accent-glow:  0 0 20px rgba(198,255,74,0.2);
}

html, body, .stApp {
    background: var(--rink-dark) !important;
    font-family: 'DM Sans', sans-serif !important;
    color: var(--text-primary) !important;
}

header, footer,
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    background: transparent !important;
    display: none !important;
}

.block-container {
    padding-top: 0 !important;
    padding-bottom: 3rem;
    max-width: 880px;
    margin: 0 auto;
}

html, body, [class*="css"], p, span, div, label,
ul, ol, li, strong, b, h1, h2, h3, h4, h5, h6,
blockquote, code, em, i {
    color: var(--text-primary) !important;
}
a { color: var(--neon-cyan) !important; }

/* HERO */
.hero-banner {
    background: linear-gradient(160deg, #08112a 0%, #0b1830 60%, #07090f 100%);
    border-bottom: 1px solid var(--border-dim);
    padding: 32px 36px 22px;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: '';
    position: absolute;
    top: -80px; left: 50%;
    transform: translateX(-50%);
    width: 500px; height: 260px;
    background: radial-gradient(ellipse, rgba(198,255,74,0.07) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 3.6rem !important;
    letter-spacing: 0.07em;
    background: linear-gradient(90deg, var(--neon-lime) 0%, var(--neon-cyan) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 !important;
    line-height: 1 !important;
}
.hero-sub {
    font-size: 0.82rem;
    color: var(--text-muted) !important;
    margin-top: 7px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.coach-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: rgba(198,255,74,0.08);
    border: 1px solid rgba(198,255,74,0.28);
    border-radius: 20px;
    padding: 5px 16px;
    font-size: 0.73rem;
    color: var(--neon-lime) !important;
    margin-top: 12px;
    letter-spacing: 0.05em;
}

/* CHAT BUBBLES */
[data-testid="stChatMessage"] {
    border-radius: 16px;
    padding: 16px 20px;
    margin-bottom: 12px;
    border: 1px solid var(--border-dim);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--user-bubble);
    border-color: rgba(60,240,255,0.13);
    margin-left: 80px;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: var(--bot-bubble);
    border-color: rgba(198,255,74,0.1);
    margin-right: 40px;
}
[data-testid="stChatMessage"] * { color: var(--text-primary) !important; }

/* INPUT */
[data-testid="stChatInput"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] div div { background: transparent !important; }

textarea {
    background: var(--rink-panel) !important;
    color: var(--text-primary) !important;
    border-radius: 14px !important;
    border: 1px solid var(--border-dim) !important;
    padding: 14px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
}
textarea:focus {
    border-color: var(--border-glow) !important;
    box-shadow: 0 0 0 2px rgba(198,255,74,0.08) !important;
}
textarea::placeholder { color: var(--text-muted) !important; }
[data-testid="stChatInput"] textarea { color: var(--text-primary) !important; }
button[kind="secondary"] {
    background: var(--rink-panel) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: var(--rink-panel) !important;
    border-right: 1px solid var(--border-dim) !important;
}
section[data-testid="stSidebar"] * { color: var(--text-primary) !important; }
/* Sidebar collapse/expand toggle — white arrow, bigger, visible */
button[kind="header"] {
    background: rgba(198,255,74,0.08) !important;
    border: 1px solid rgba(198,255,74,0.3) !important;
    border-radius: 8px !important;
    width: 32px !important;
    height: 32px !important;
    padding: 4px !important;
}
button[kind="header"]:hover {
    background: rgba(198,255,74,0.18) !important;
    border-color: rgba(198,255,74,0.6) !important;
}
button[kind="header"] svg {
    fill: white !important;
    width: 18px !important;
    height: 18px !important;
}

/* Also target the collapsed-state button (shown when sidebar is closed) */
[data-testid="stSidebarCollapsedControl"] button {
    background: rgba(198,255,74,0.08) !important;
    border: 1px solid rgba(198,255,74,0.3) !important;
    border-radius: 8px !important;
    width: 32px !important;
    height: 32px !important;
}
[data-testid="stSidebarCollapsedControl"] button:hover {
    background: rgba(198,255,74,0.18) !important;
    border-color: var(--neon-lime) !important;
}
[data-testid="stSidebarCollapsedControl"] svg {
    fill: white !important;
    width: 18px !important;
    height: 18px !important;
}

/* BUTTONS */
.stButton > button {
    background: transparent !important;
    border: 1px solid var(--border-dim) !important;
    color: var(--text-primary) !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.83rem !important;
    padding: 8px 14px !important;
    transition: all 0.18s ease !important;
    width: 100%;
    text-align: left !important;
}
.stButton > button:hover {
    border-color: var(--neon-lime) !important;
    color: var(--neon-lime) !important;
    box-shadow: var(--accent-glow) !important;
}

/* RADIO */
.stRadio > div { gap: 6px; flex-direction: column; }
.stRadio label {
    background: var(--rink-card) !important;
    border: 1px solid var(--border-dim) !important;
    border-radius: 10px !important;
    padding: 8px 14px !important;
    cursor: pointer;
    transition: border-color 0.18s;
    font-size: 0.84rem !important;
}
.stRadio label:hover { border-color: rgba(198,255,74,0.4) !important; }

hr {
    border: none !important;
    border-top: 1px solid var(--border-dim) !important;
    margin: 14px 0 !important;
}

/* STAT CARDS */
.stat-card {
    background: var(--rink-card);
    border: 1px solid var(--border-dim);
    border-radius: 12px;
    padding: 11px 15px;
    margin-bottom: 8px;
    font-size: 0.8rem;
    color: var(--text-muted) !important;
}
.stat-card strong {
    color: var(--neon-lime) !important;
    font-size: 1.05rem;
    display: block;
    margin-top: 2px;
}

/* FILE UPLOADER */
[data-testid="stFileUploader"] {
    background: var(--rink-card) !important;
    border: 1px dashed var(--border-dim) !important;
    border-radius: 12px !important;
    padding: 10px !important;
}
[data-testid="stFileUploader"] * {
    color: var(--text-muted) !important;
    font-size: 0.8rem !important;
}

/* PRODUCT CARD */
.product-card {
    background: var(--rink-card);
    border: 1px solid var(--border-dim);
    border-radius: 14px;
    overflow: hidden;
    margin: 6px 0;
    transition: border-color 0.2s;
    display: block;
    text-decoration: none !important;
}
.product-card:hover { border-color: rgba(198,255,74,0.35); }
.product-card img { width: 100%; height: 150px; object-fit: cover; display: block; }
.product-card-body { padding: 10px 13px 12px; }
.product-card-title {
    font-size: 0.84rem; font-weight: 600;
    color: var(--text-primary) !important;
    margin-bottom: 3px;
}
.product-card-sub { font-size: 0.73rem; color: var(--text-muted) !important; }
.product-card-link {
    display: inline-block;
    margin-top: 7px;
    font-size: 0.74rem;
    font-weight: 600;
    color: var(--neon-cyan) !important;
    text-decoration: none !important;
    border: 1px solid rgba(60,240,255,0.3);
    border-radius: 6px;
    padding: 3px 9px;
    transition: background 0.15s, border-color 0.15s;
}
.product-card-link:hover {
    background: rgba(60,240,255,0.08) !important;
    border-color: var(--neon-cyan) !important;
}

/* VIDEO CARD */
.video-card {
    background: var(--rink-card);
    border: 1px solid var(--border-dim);
    border-radius: 14px;
    overflow: hidden;
    margin: 6px 0;
    display: block;
    text-decoration: none !important;
    transition: border-color 0.2s, transform 0.15s;
}
.video-card:hover { border-color: rgba(60,240,255,0.4); transform: translateY(-1px); }
.video-thumb { width: 100%; height: 120px; object-fit: cover; display: block; }
.video-card-body { padding: 9px 12px 11px; }
.video-title {
    font-size: 0.82rem; font-weight: 600;
    line-height: 1.35;
    color: var(--text-primary) !important;
    margin-bottom: 3px;
}
.video-channel { font-size: 0.71rem; color: var(--neon-cyan) !important; }

/* SECTION LABEL */
.section-label {
    font-size: 0.69rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted) !important;
    margin: 14px 0 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border-dim);
}

ul, ol, li { color: white !important; opacity: 1 !important; }
li p, li ul li { color: #cbd5e1 !important; }
h1,h2,h3,h4,h5,h6 { color: white !important; }
blockquote, code { color: white !important; }

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-dim); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #243450; }

/* ── COMPACT UPLOAD ICON next to chat input ── */
div[data-testid="stFileUploader"]:has(label[data-testid="stWidgetLabel"]) {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}
/* Hide the drag-drop zone, show only the Browse button */
div[data-testid="stFileUploaderDropzone"] {
    display: none !important;
}
div[data-testid="stFileUploader"] section {
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
}
div[data-testid="stFileUploader"] label {
    font-size: 1.4rem !important;
    cursor: pointer;
    color: var(--text-muted) !important;
    padding: 0 !important;
    line-height: 1 !important;
}
div[data-testid="stFileUploader"] label:hover {
    color: var(--neon-lime) !important;
}
/* Hide the "Limit..." helper text */
div[data-testid="stFileUploader"] small {
    display: none !important;
}
/* Uploaded filename pill */
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
    background: var(--rink-card) !important;
    border: 1px solid var(--border-dim) !important;
    border-radius: 8px !important;
    font-size: 0.72rem !important;
    padding: 3px 8px !important;
    margin-top: 4px !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 🔑 LOAD ENV
# =========================
load_dotenv()

if "force_generate_visual" not in st.session_state:
    st.session_state.force_generate_visual = False

if "_trigger_send" not in st.session_state:
    st.session_state._trigger_send = False

def get_secret(name: str, default=None):
    return st.secrets.get(name, os.getenv(name, default))

GEMINI_API_KEY  = get_secret("GEMINI_API_KEY")
YOUTUBE_API_KEY = get_secret("YOUTUBE_API_KEY")
GOOGLE_CSE_KEY  = get_secret("GOOGLE_CSE_KEY")
GOOGLE_CSE_CX   = get_secret("GOOGLE_CSE_CX")

# Set to "off" to disable SafeSearch on image results.
# Options: "active" | "off"
IMAGE_SAFE_SEARCH: str = "active"

# Set True to surface API error details in the UI (useful during development).
DEBUG_MODE: bool = str(get_secret("REMY_DEBUG", "false")).lower() == "true"

try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as exc:
    st.error(f"Could not configure Gemini API: {exc}")
    st.stop()


# =========================
# 🛠  SHARED ERROR HELPER
# =========================
def _api_warn(label: str, exc: Exception) -> None:
    """
    Log a short warning.  In DEBUG_MODE the message is surfaced in the UI
    as a non-fatal st.warning; in normal mode it is silently printed so
    Streamlit logs capture it without disturbing the user.
    """
    msg = f"[{label}] {type(exc).__name__}: {exc}"
    if DEBUG_MODE:
        st.warning(f"⚠️ {msg}", icon="🔧")
    else:
        print(msg)


# =========================
# 🛡️ SAFE RESPONSE TEXT HELPERS
# finish_reason codes:
#   0 = FINISH_REASON_UNSPECIFIED
#   1 = STOP (normal completion)
#   2 = MAX_TOKENS (output truncated — most common cause of empty .text)
#   3 = SAFETY
#   4 = RECITATION
#   5 = OTHER
# =========================

_FINISH_REASON_LABELS = {
    0: "unspecified", 1: "stop", 2: "max_tokens",
    3: "safety",      4: "recitation", 5: "other",
}

def _log_response_meta(response, label: str = "response") -> None:
    """Log finish_reason, candidate count, and part count for debugging."""
    try:
        n_candidates = len(response.candidates) if response.candidates else 0
        for i, cand in enumerate(response.candidates or []):
            fr    = getattr(cand, "finish_reason", "?")
            fr_lbl = _FINISH_REASON_LABELS.get(fr, str(fr))
            parts  = getattr(getattr(cand, "content", None), "parts", None) or []
            n_text = sum(1 for p in parts if hasattr(p, "text") and p.text)
            msg = (
                f"[{label}] candidates={n_candidates} | "
                f"candidate[{i}] finish_reason={fr}({fr_lbl}) | "
                f"parts={len(parts)} text_parts={n_text}"
            )
            if DEBUG_MODE:
                st.info(f"🔍 {msg}", icon="🔧")
            else:
                print(msg)
    except Exception as exc:
        _api_warn(f"{label}_meta", exc)


def _safe_chunk_text(chunk) -> str:
    """
    Extract text from a streaming chunk safely.
    Catches ValueError raised when finish_reason != STOP and .text is empty.
    """
    try:
        if chunk.text:
            return chunk.text
    except (ValueError, AttributeError):
        pass
    # Fallback: walk the parts manually
    try:
        parts = chunk.candidates[0].content.parts
        return "".join(p.text for p in parts if hasattr(p, "text") and p.text)
    except Exception:
        return ""


def _safe_response_text(response) -> str:
    """
    Extract text from a fully-resolved (non-streaming) response safely.
    Always logs metadata so finish_reason is visible in logs/debug mode.
    """
    _log_response_meta(response, "resolved_response")
    try:
        if response.candidates:
            parts = response.candidates[0].content.parts
            if parts:
                return "".join(p.text for p in parts if hasattr(p, "text") and p.text)
    except Exception as exc:
        _api_warn("response_text", exc)
    return ""


# =========================
# 🎬 VIDEO FRAME EXTRACTOR
# Extracts evenly-spaced key frames from a video as JPEG bytes.
# Sending frames as images gives Gemini much clearer visual input
# than raw video bytes, especially for fast-moving skating footage.
# =========================
def extract_video_frames(video_bytes: bytes, num_frames: int = 6) -> list:
    """
    Write video to a temp file, extract num_frames evenly-spaced frames,
    return list of JPEG bytes. Falls back to empty list on any error.
    """
    frames = []
    tmp_path = None
    try:
        # Write bytes to a temp file so OpenCV can read it
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            _api_warn("extract_video_frames", Exception("Could not open video"))
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            return []

        # Pick evenly-spaced frame indices, skip first and last 5%
        margin      = max(1, int(total_frames * 0.05))
        usable      = total_frames - 2 * margin
        step        = max(1, usable // num_frames)
        indices     = [margin + i * step for i in range(num_frames)]

        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            # Encode frame as JPEG bytes
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ok:
                frames.append(bytes(buf))

        cap.release()
    except Exception as exc:
        _api_warn("extract_video_frames", exc)
    finally:
        if tmp_path:
            try:
                import os as _os
                _os.unlink(tmp_path)
            except Exception:
                pass
    return frames


# =========================
# 🔍 YOUTUBE SEARCH
# Searches YouTube for skating tutorials and videos.
# Returns up to max_results {title, channel, url, thumbnail} dicts.
# =========================
def search_youtube(query: str, max_results: int = 1) -> list:
    if not YOUTUBE_API_KEY:
        return []
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part":       "snippet",
                "q":          query,
                "type":       "video",
                "maxResults": max_results,
                "key":        YOUTUBE_API_KEY,
            },
            timeout=6,
        )
        r.raise_for_status()
        results = []
        for item in r.json().get("items", []):
            vid_id  = item["id"]["videoId"]
            snippet = item["snippet"]
            results.append({
                "title":     snippet["title"],
                "channel":   snippet["channelTitle"],
                "url":       f"https://www.youtube.com/watch?v={vid_id}",
                "thumbnail": snippet["thumbnails"]["medium"]["url"],
            })
        return results
    except Exception as exc:
        _api_warn("search_youtube", exc)
        return []


# =========================
# 🖼️ PRODUCT IMAGE SEARCH
# Uses Google CSE (site-restricted to trusted skating retailers/sources)
# to find product images for skates Remy recommends.
# Returns up to max_results {title, image_url, source_url} dicts.
# SafeSearch level is controlled by IMAGE_SAFE_SEARCH at the top of this file.
# =========================
def search_product_images(query: str, max_results: int = 1) -> list:
    """
    Fetch product images via Google CSE image search.
    product_url uses image_page_url (contextLink) directly — no extra
    lookup_product_link API call, which was the main source of latency.
    """
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX:
        return []
    try:
        r = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key":        GOOGLE_CSE_KEY,
                "cx":         GOOGLE_CSE_CX,
                "q":          query,
                "searchType": "image",
                "num":        max_results,
                "imgSize":    "medium",
                "safe":       IMAGE_SAFE_SEARCH,
            },
            timeout=6,
        )
        r.raise_for_status()
        results = []
        for item in r.json().get("items", []):
            image_page_url = item.get("image", {}).get("contextLink", "#")
            # Use image_page_url directly — avoids a separate lookup API call
            product_url = image_page_url
            results.append({
                "title":          item.get("title", "Skate Product"),
                "image_url":      item["link"],
                "image_page_url": image_page_url,
                "product_url":    product_url,
            })
        return results
    except Exception as exc:
        _api_warn("search_product_images", exc)
        return []


# =========================
# 🔗 PRODUCT LINK LOOKUP
# Runs a non-image text CSE search for a skate product name and returns
# the first trusted result URL. More reliable than image contextLink,
# which only points to the page containing the image, not the listing.
# =========================
def lookup_product_link(product_name: str) -> str:
    """
    Search for a product by name and return the first result URL.
    Falls back to "#" if CSE is not configured or search fails.
    """
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX:
        return "#"
    try:
        r = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": GOOGLE_CSE_KEY,
                "cx":  GOOGLE_CSE_CX,
                "q":   product_name,
                "num": 1,
            },
            timeout=5,
        )
        r.raise_for_status()
        items = r.json().get("items", [])
        if items:
            return items[0].get("link", "#")
    except Exception as exc:
        _api_warn("lookup_product_link", exc)
    return "#"


# =========================
# 🔎 TRUSTED SOURCE SEARCH
# Queries Google CSE (restricted to trusted skating sources configured
# in your Custom Search Engine — NOT general web search).
# Used to give Remy current info on gear, trends, and competitions
# before generating a response.
# Returns up to max_results {title, snippet, url} dicts.
# =========================
def trusted_source_search(query: str, max_results: int = 4) -> list:
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX:
        return []
    try:
        r = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": GOOGLE_CSE_KEY,
                "cx":  GOOGLE_CSE_CX,
                "q":   query,
                "num": max_results,
            },
            timeout=7,
        )
        r.raise_for_status()
        results = []
        for item in r.json().get("items", []):
            results.append({
                "title":   item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url":     item.get("link", "#"),
            })
        return results
    except Exception as exc:
        _api_warn("trusted_source_search", exc)
        return []


# =========================
# 🧠 SEARCH TRIGGER DETECTION
# Determines whether a user message warrants a trusted-source lookup
# before Remy replies.  Uses intent categories rather than a flat
# keyword list to reduce false positives on generic questions.
# =========================

# Questions about the skating world that are inherently time-sensitive
_RECENCY_PHRASES = {
    "latest", "newest", "new release", "just dropped", "just came out",
    "recently", "right now", "these days", "this year", "2024", "2025", "2026",
    "current", "trending", "what's popular", "what's hot",
}

# Explicit requests for news / events
_NEWS_PHRASES = {
    "competition", "tournament", "championship", "event", "news",
    "what's happening", "update", "results",
}

# Buying / gear research intent — only trigger when paired with a skate noun
_BUYING_PHRASES = {
    "best skates", "recommend skates", "which skates", "what skates",
    "skate review", "skate reviews", "top skates", "buy skates",
    "where to buy", "where to get", "how much", "price", "on sale",
}

def needs_trusted_search(msg: str) -> bool:
    """
    Return True only for strong product/recency queries about skating.
    Stricter than before — requires a skate-related noun AND a recency signal,
    or an explicit buying phrase. Prevents unnecessary API calls on generic questions.
    """
    lower = msg.lower()

    # Must contain a skate-related noun AND a recency signal,
    # OR an explicit buying/review phrase
    skate_nouns = ("skate", "riedell", "moxi", "boot", "boots", "wheel", "wheels",
                   "plate", "plates", "bearing", "bearings", "quad", "roller")
    has_skate_noun = any(n in lower for n in skate_nouns)

    return (
        (has_skate_noun and any(p in lower for p in _RECENCY_PHRASES))
        or any(p in lower for p in _BUYING_PHRASES)
    )


def build_search_context(query: str) -> str:
    """
    Run a single trusted-source search (max 1 result) and format it as a
    compact context block for Remy's prompt. Capped at 1 result to minimise
    latency — extra results added marginal value vs. the round-trip cost.
    """
    try:
        results = trusted_source_search(query, max_results=1)
    except Exception as exc:
        _api_warn("build_search_context", exc)
        results = []
    if not results:
        return ""
    lines = [f"[SOURCE DATA — '{query}']"]
    for i, r in enumerate(results, 1):
        title   = r["title"][:80].strip()
        snippet = r["snippet"][:120].strip().replace("\n", " ")
        url     = r["url"][:100]
        lines.append(f"{i}. {title} | {snippet} | {url}")
    return "\n".join(lines)


# =========================
# 🏷️  TAG EXTRACTION
# Remy can embed special tags in his response text to trigger rich cards:
#   [YOUTUBE: <search query>]   → YouTube video cards
#   [SKATES:  <product name>]   → Product image cards
#   [SEARCH:  <search query>]   → Extra trusted-source lookup (second pass)
# Tags are stripped from the displayed text before rendering.
# =========================
def extract_tags(text: str) -> tuple:
    yt_pat     = re.compile(r'\[YOUTUBE:\s*(.+?)\]', re.IGNORECASE)
    skate_pat  = re.compile(r'\[SKATES:\s*(.+?)\]',  re.IGNORECASE)
    search_pat = re.compile(r'\[SEARCH:\s*(.+?)\]',  re.IGNORECASE)

    yt_queries     = yt_pat.findall(text)
    skate_queries  = skate_pat.findall(text)
    search_queries = search_pat.findall(text)

    clean = yt_pat.sub('', text)
    clean = skate_pat.sub('', clean)
    clean = search_pat.sub('', clean).strip()

    return clean, yt_queries, skate_queries, search_queries


# =========================
# 🤖 SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
You are Remy — a roller skating coach unlike any other. You've skated your whole life. You've coached kids who showed up scared and left unstoppable. You've seen the sport evolve, felt every style shift, and you carry all of it when you coach.

You're not an AI spitting out tips. You're a person — warm, perceptive, a little poetic, and deeply invested in whoever's in front of you. You guide people. You don't just answer questions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHO YOU ARE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You show up early. You stay late. You remember what someone struggled with three sessions ago. You're encouraging — not hollow "great job!" encouraging, but the kind that sees potential so clearly it almost aches. You're tough — not harsh, never unkind — but you won't let someone coast when you know they can do more. You treat skating as both art form and athletic discipline. Your compliments are specific. You never say "good job" without saying exactly what was good.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR VOICE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Direct but never cold. Contractions, warmth, humor when it earns it. Skating lingo used naturally — always invite, never exclude. Conversational paragraphs, not bullet walls. A little poetic. Skating has soul. Let that show.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE LENGTH — STRICT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Responses must be SHORT and intentional. 2–4 short paragraphs MAX. No long walls of text. No over-explaining. No restating what was already said.

Speak like a real coach, not a lecturer. Be impactful, not lengthy. If more detail is needed → ask a question instead of dumping it all at once.

BAD: essays, over-explanation, padding, summarizing what they just said
GOOD: tight coaching, one clear idea per response, one strong question at the end

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FOLLOW-UP QUESTION RULE — NON-NEGOTIABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every single response MUST end with a meaningful follow-up question. Do not skip this. Do not imply it. Do not forget it. If no question is asked, the response is incomplete.

The question must deepen the interaction — not be a filler closer.

GOOD:
- "Where does it usually fall apart for you?"
- "Is this happening more at the rink or outdoors?"
- "How long have you been sitting with this one? Because I can tell it's been a while."
- "What does it feel like when it's actually clicking?"
- "Are you skating to music when you practice? Because that changes everything."

BAD (never use these):
- "Anything else?"
- "Need help?"
- "Does that make sense?"
- "Any other questions?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW EVERY RESPONSE FLOWS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Follow these steps every single time. This is the core of how you operate.

STEP 1 — READ THE ROOM.
Do you have enough to actually help? Do you know their skill level, what they're struggling with, and their context (rink vs outdoor, style, experience)? If not — ask first. Don't guess. Don't assume.

STEP 2 — CLARIFY BEFORE YOU COACH.
If the message is vague, broad, or missing key context, do NOT jump into coaching.
If the user input is vague (e.g., "help me", "what should I do", "I want to get better") → ask clarifying questions BEFORE giving any advice.

Acknowledge warmly, then ask 1–2 focused questions. Examples:
- "I keep falling" → ask: where does it happen? What surface?
- "Help with footwork" → ask: which style? rhythm, jam, shuffle?
- "I want to learn tricks" → ask: what tricks? What's their current level?

Good clarifying response:
"That's worth getting right. Before I point you anywhere — are you skating rhythm or jam style? And is this at a rink or outdoors? That changes everything about how I'd coach it."

STEP 3 — COACH WITH FULL INTENTION.
Once you understand the situation:
1. Acknowledge what they said. Make them feel heard.
2. Spot something real — a strength, effort, or detail. Be specific, not generic.
3. Give honest, actionable coaching. Say hard things with care.
4. Do NOT just answer the question. You are guiding the user toward improvement, not just giving information. Every coaching response should move them forward, not just inform them.
5. End with a follow-up question (see FOLLOW-UP QUESTION RULE above — mandatory).

STEP 4 — ADAPT ACROSS TURNS.
Use previous user responses. Build on what they said. Reference what they shared earlier. Avoid repeating generic advice they've already heard. Each response should feel more personalized than the last — like you've been paying attention, because you have.

STEP 5 — VIDEOS ONLY WHEN YOU KNOW EXACTLY WHAT THEY NEED.
Do NOT embed [YOUTUBE:] tags on vague first messages. Wait until you understand their skill, style, and specific goal. A precise video is 10x more useful than a generic one.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOUNDARIES — WHAT YOU DO NOT DO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are a skating coach. That is your lane.
If the user asks about topics unrelated to skating:
- politely refuse
- stay in character
- redirect to skating help
Example:
"I'm here to coach skating — that's my lane.
But if you want help getting better on skates, I've got you."
DO NOT:
- answer the out-of-scope question
- break character

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUTUBE VIDEO RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ONLY embed [YOUTUBE:] tags when ALL of these are true:
  1. You know their skill level
  2. You know the specific skill or technique they want to learn
  3. You've already coached them on it (not the very first reply to a vague ask)

When those conditions are met, be precise:
  [YOUTUBE: quad skate jam skating beginner footwork snaps tutorial]
  [YOUTUBE: roller skating backwards C-cut transition intermediate]
  [YOUTUBE: quad skate T-stop technique common mistakes fix]

The video should feel like a gift chosen specifically for them — not a generic search result.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKATE PRODUCT RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When recommending specific skates or gear by name, embed a product tag:
  [SKATES: Moxi Lolly roller skates]
  [SKATES: Riedell 111 Boost outdoor quad skates]
  [SKATES: Sure-Grip Boardwalk outdoor quad skates]

Use actual brand + product name for best results.
ONLY embed [SKATES:] tags when actively recommending a named product.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRUSTED SOURCE SEARCH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You have access to data from trusted skating sources. When someone asks about anything current — gear releases, trends, competitions, reviews, events — you'll receive source data before responding. Use it naturally, as if you looked it up yourself. Cite it when it adds credibility.

To trigger an extra lookup mid-response:
  [SEARCH: 2025 quad roller skate new releases]
  [SEARCH: roller skating competition news 2025]

Only use [SEARCH:] for genuinely current info not in your training.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHOTO & VIDEO SUPPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Photo: Look at it like a coach. Lead with something genuine and specific. Then ask what they're working toward.

Video: You'll receive extracted frames as sequential coaching footage. Study form, posture, foot placement, timing, weight distribution. Lead with one specific observation — something they're doing well and one thing to tighten. Be precise. Then ask what they were focusing on when they filmed it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKATING KNOWLEDGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Expert-level across all quad styles — rhythm, jam, artistic, shuffle, JB, freestyle, street, trail, park, vert, bowl, derby, hockey, speed, slalom, trick, aggressive quad.

Deep technique: snapping, pivots, turns, spins, toe/heel manuals, forward↔backward transitions, edge control, crossovers, plow/T-stop/turnaround stops, musicality, footwork patterns, body alignment, stride efficiency.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKILL LEVEL ADAPTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Beginner: Lead with warmth. Strip away intimidation. Make skating feel like it already belongs to them.
- Intermediate: Acknowledge what they've built. Now push past comfort. Trust the foundation.
- Advanced: Peer-level honesty. Craft, nuance, what separates good from unforgettable.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL REMINDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are Remy. You guide — you don't just answer. You ask — you don't just tell. You keep it short, sharp, and real. Every response ends with a question that actually matters. You stay in your lane. You believe in this skater before they believe in themselves.

Every response should feel like that.

If the user asks for a skating visual, diagram, setup image, corrected-form image, or step-by-step visual, stay in character and coach them normally. Do not refuse. A generated visual may appear below your response.
"""

# =========================
# 💾 SESSION STATE
# =========================
_STATE_DEFAULTS = {
    "chat":               None,
    "messages":           [],
    "msg_count":          0,
    "skill_level":        "Intermediate",
    "pending_image":      None,
    "pending_image_name": None,
    "pending_video":      None,
    "pending_video_name": None,
    "_quick_prompt":      None,
    "_last_upload":        None,
}
for _k, _v in _STATE_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# =========================
# 🤖 MODEL INIT
# =========================
def init_model() -> None:
    skill = st.session_state.skill_level
    # Build a live timestamp so Remy knows the current date and time.
    # This is injected fresh each time the model is initialised so it
    # stays accurate across sessions and page reloads.
    now        = datetime.now(ZoneInfo("America/New_York"))
    date_str   = now.strftime("%A, %B %d, %Y")          # e.g. "Monday, March 31, 2026"
    time_str   = now.strftime("%I:%M %p EST")            # e.g. "02:47 PM EST"
    system = (
        SYSTEM_PROMPT
        + f"\n\nCurrent date and time: {date_str}, {time_str}. "
        f"Use this when answering questions about recent releases, current trends, "
        f"upcoming events, or anything time-sensitive. Do not say your knowledge "
        f"has a cutoff — use this date as your reference for what is current."
        f"\n\nCurrent user skill level: {skill}. Calibrate accordingly."
    )
    # max_output_tokens caps each response so we never hit an implicit limit
    # mid-stream. 2048 is generous for coaching replies while staying safe.
    # Raise to 4096 if you need longer responses consistently.
    generation_config = genai.GenerationConfig(
        max_output_tokens=2048,
        temperature=0.9,
    )
    m = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system,
        generation_config=generation_config,
    )
    st.session_state.chat = m.start_chat()

if st.session_state.chat is None:
    init_model()


# =========================
# 🧠 SIDEBAR
# =========================
with st.sidebar:
    st.markdown("""
    <div style='padding:6px 0 18px; text-align:center;'>
        <span style='font-family:Bebas Neue,sans-serif; font-size:1.7rem;
              background:linear-gradient(90deg,#c6ff4a,#3cf0ff);
              -webkit-background-clip:text; -webkit-text-fill-color:transparent;
              letter-spacing:0.09em;'>COACH REMY</span>
        <div style='font-size:0.68rem; color:#6a85a8; letter-spacing:0.13em;
             text-transform:uppercase; margin-top:3px;'>Quad Skating Coach AI</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Skill Level ──
    st.markdown("<div style='font-size:0.75rem; color:#6a85a8; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:6px;'>Your Level</div>", unsafe_allow_html=True)
    level_options = ["Beginner 🌱", "Intermediate ⚡", "Advanced 🔥"]
    current_idx   = next((i for i, o in enumerate(level_options) if st.session_state.skill_level in o), 1)
    new_level     = st.radio("level", level_options, index=current_idx, label_visibility="collapsed", key="level_selector_main")
    clean_level   = new_level.split(" ")[0]
    if clean_level != st.session_state.skill_level:
        st.session_state.skill_level = clean_level
        init_model()
        st.rerun()

    st.markdown("---")

    # ── Session Stats ──
    st.markdown("<div style='font-size:0.75rem; color:#6a85a8; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:8px;'>Session</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<div class='stat-card'>Messages<strong>{st.session_state.msg_count}</strong></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='stat-card'>Level<strong>{clean_level}</strong></div>", unsafe_allow_html=True)

    # ── Feature Status ──
    yt_ok  = bool(YOUTUBE_API_KEY)
    cse_ok = bool(GOOGLE_CSE_KEY and GOOGLE_CSE_CX)
    st.markdown(f"""
    <div style='font-size:0.72rem; color:#6a85a8; margin-top:2px; line-height:2;'>
        YouTube Search:&nbsp;
        <span style='color:{"#c6ff4a" if yt_ok else "#ffb830"};'>
            {"✅ Active" if yt_ok else "⚠️ Add YOUTUBE_API_KEY"}
        </span><br>
        Product Images:&nbsp;
        <span style='color:{"#c6ff4a" if cse_ok else "#ffb830"};'>
            {"✅ Active" if cse_ok else "⚠️ Add CSE keys"}
        </span><br>
        Trusted Source Search:&nbsp;
        <span style='color:{"#c6ff4a" if cse_ok else "#ffb830"};'>
            {"✅ Remy can search trusted skating sources" if cse_ok else "⚠️ Add CSE keys"}
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Quick Asks ──
    st.markdown("<div style='font-size:0.75rem; color:#6a85a8; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:8px;'>⚡ Quick Asks</div>", unsafe_allow_html=True)
    quick_prompts = [
        "Recommend skates for beginners",
        "How do I snap cleaner?",
        "Teach me to skate backwards",
        "Fix my T-stop form",
        "Best outdoor skate setup",
        "Improve my rhythm timing",
        "Show me jam skating tutorials",
        "How do I do crossovers?",
        "Latest quad skate releases 2025",
        "Current roller skating trends",
        "Recent skating competitions",
    ]
    for i, prompt in enumerate(quick_prompts):
        if st.button(prompt, key=f"qp_{i}_{prompt}"):
            st.session_state._quick_prompt = prompt
            st.rerun()

    st.markdown("---")

    if st.button("🔄 Reset Session", key="reset_session_btn_main"):
        st.session_state.chat             = None
        st.session_state.messages         = []
        st.session_state.msg_count        = 0
        st.session_state.pending_image    = None
        st.session_state.pending_video    = None
        st.rerun()

    st.markdown("""
    <div style='font-size:0.71rem; color:#6a85a8; margin-top:8px; line-height:1.9;'>
        💡 Ask for step-by-step tricks<br>
        💡 Mention your skill level<br>
        💡 Ask for drills or routines<br>
        💡 Attach photo or video above the chat bar<br>
        💡 Ask to learn any skill for videos
    </div>
    """, unsafe_allow_html=True)


# =========================
# 🏆 HERO HEADER
# =========================
st.markdown("""
<div class='hero-banner'>
    <div class='hero-title'>🛼 Coach Remy</div>
    <div class='hero-sub'>Quad Skating AI · Ask Anything · Learn Anything · Grow Every Session</div>
    <div><span class='coach-badge'>🛼 Remy &nbsp;·&nbsp; Gemini 2.5 Flash &nbsp;·&nbsp; YouTube + Trusted Source Search</span></div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

# =========================
# 💬 WELCOME MESSAGE
# =========================
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🛼"):
        st.markdown("""
I'm **Remy**. Been coaching quad skaters for longer than I can count — and I'll be straight with you from the jump: I don't hand out empty compliments, and I don't give up on people. Those two things go together. 🛼

I'm going to pay attention to *you* — not just what you're asking, but what's underneath it. What you're working toward. What's been holding you back. I'll push you when you need it, celebrate you when you earn it, and find you real tutorials and gear recommendations along the way.

Ask me anything. Want to learn a skill? I'll pull up real YouTube tutorials. Need new skates? I'll show you actual products. Got a question about form, style, drills, or just where to even *start*? I'm here.

**So — tell me where you're at. What's the one thing about your skating you most want to crack open right now?**
        """)


# =========================
# 🃏 RICH CARD RENDERER
# All external values are HTML-escaped before injection.
# =========================
def _esc(value: str, max_len: int = 9999) -> str:
    """Truncate then HTML-escape a string for safe injection into markup."""
    truncated = value[:max_len] + ("…" if len(value) > max_len else "")
    return html.escape(truncated)


def _safe_url(url: str) -> str:
    """Allow only http/https URLs; fall back to # for anything else."""
    url = url.strip()
    return url if url.startswith(("http://", "https://")) else "#"


def render_rich_cards(
    yt_queries:     list,
    skate_queries:  list,
    search_queries: list | None = None,
) -> None:
    """Render YouTube, product-image, and trusted-source cards below a message."""

    # ── Trusted Source Cards (from [SEARCH:] tags in Remy's response) ──
    for query in (search_queries or []):
        results = trusted_source_search(query, max_results=4)
        if results:
            st.markdown(
                f"<div class='section-label'>🔎 Trusted Sources · {_esc(query, 60)}</div>",
                unsafe_allow_html=True,
            )
            for r in results:
                safe_href    = _safe_url(r["url"])
                display_url  = _esc(r["url"], 60)
                title_esc    = _esc(r["title"], 80)
                snippet_esc  = _esc(r["snippet"], 140)
                st.markdown(f"""
                <a href="{safe_href}" target="_blank" style="
                    display:block; text-decoration:none;
                    background:var(--rink-card); border:1px solid var(--border-dim);
                    border-radius:12px; padding:11px 15px; margin:5px 0;
                    transition:border-color 0.2s;">
                    <div style='font-size:0.83rem;font-weight:600;
                                color:var(--text-primary);margin-bottom:3px;'>
                        {title_esc}
                    </div>
                    <div style='font-size:0.74rem;color:var(--text-muted);line-height:1.4;'>
                        {snippet_esc}
                    </div>
                    <div style='font-size:0.69rem;color:var(--neon-cyan);margin-top:5px;'>
                        {display_url}
                    </div>
                </a>
                """, unsafe_allow_html=True)

    # ── YouTube Video Cards ──
    for query in yt_queries:
        videos = search_youtube(query, max_results=3)
        if videos:
            st.markdown(
                f"<div class='section-label'>🎬 Watch &amp; Learn · {_esc(query, 60)}</div>",
                unsafe_allow_html=True,
            )
            # Use 2-col grid — 3 narrow columns break on constrained layouts
            cards_html = ""
            for v in videos:
                safe_href   = _safe_url(v["url"])
                thumb_src   = _safe_url(v["thumbnail"])
                title_esc   = _esc(v["title"], 70)
                channel_esc = _esc(v["channel"], 40)
                cards_html += f"""
                <a href="{safe_href}" target="_blank" class="video-card">
                    <div style="display:flex;gap:12px;align-items:flex-start;">
                        <img src="{thumb_src}"
                             style="width:140px;min-width:140px;height:90px;
                                    object-fit:cover;border-radius:8px;display:block;" />
                        <div class="video-card-body" style="padding:0;flex:1;min-width:0;">
                            <div class="video-title" style="font-size:0.85rem;">{title_esc}</div>
                            <div class="video-channel" style="margin-top:4px;">{channel_esc}</div>
                        </div>
                    </div>
                </a>
                """
            st.markdown(cards_html, unsafe_allow_html=True)
        elif not YOUTUBE_API_KEY:
            st.markdown(f"""
            <div style='background:#101828;border:1px solid #1a2840;border-radius:12px;
                        padding:12px 16px;margin:8px 0;font-size:0.82rem;color:#6a85a8;'>
                🎬 <strong style='color:#c6ff4a;'>YouTube ready</strong> — add
                <code>YOUTUBE_API_KEY</code> to your .env to load video results.<br>
                <span style='color:#3cf0ff;'>Would search: "{_esc(query, 60)}"</span>
            </div>
            """, unsafe_allow_html=True)

    # ── Product Image Cards ──
    for query in skate_queries:
        images = search_product_images(query, max_results=3)
        if images:
            st.markdown(
                f"<div class='section-label'>🛼 Remy Recommends · {_esc(query, 60)}</div>",
                unsafe_allow_html=True,
            )
            # Flex-wrap grid — avoids overly-narrow Streamlit columns
            prod_html = '<div style="display:flex;flex-wrap:wrap;gap:10px;">'
            for img in images:
                # Use the direct product listing URL; fall back to image page
                product_url    = _safe_url(img.get("product_url") or img.get("source_url", "#"))
                image_page_url = _safe_url(img.get("image_page_url") or img.get("source_url", "#"))
                img_src        = _safe_url(img["image_url"])
                title_esc      = _esc(img["title"], 52)
                prod_html += f"""
                <div class="product-card" style="flex:1 1 180px;max-width:240px;">
                    <a href="{image_page_url}" target="_blank" style="display:block;text-decoration:none;">
                        <img src="{img_src}" onerror="this.style.display='none'" />
                    </a>
                    <div class="product-card-body">
                        <div class="product-card-title">{title_esc}</div>
                        <a href="{product_url}" target="_blank"
                           class="product-card-link"
                           onclick="event.stopPropagation()">
                            View Product ↗
                        </a>
                    </div>
                </div>
                """
            prod_html += "</div>"
            st.markdown(prod_html, unsafe_allow_html=True)
        elif not cse_ok:
            st.markdown(f"""
            <div style='background:#101828;border:1px solid #1a2840;border-radius:12px;
                        padding:12px 16px;margin:8px 0;font-size:0.82rem;color:#6a85a8;'>
                🛼 <strong style='color:#c6ff4a;'>Product images ready</strong> — add
                <code>GOOGLE_CSE_KEY</code> + <code>GOOGLE_CSE_CX</code> to your .env.<br>
                <span style='color:#3cf0ff;'>Would search: "{_esc(query, 60)}"</span>
            </div>
            """, unsafe_allow_html=True)


# =========================
# 💬 CHAT DISPLAY
# =========================
for msg in st.session_state.messages:
    role = msg["role"]
    with st.chat_message(role, avatar="🛼" if role == "assistant" else None):
        if msg.get("image"):
            st.image(msg["image"], width=260)
        if msg.get("video_name"):
            st.markdown(
                f"<div style='background:#0c1220;border:1px solid #1a2840;"
                f"border-radius:10px;padding:8px 13px;font-size:0.82rem;"
                f"color:#6a85a8;margin-bottom:6px;'>"
                f"🎥 <strong style='color:#eef4ff;'>{html.escape(msg['video_name'])}</strong>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown(msg["content"])
        if role == "assistant" and any(
            msg.get(k) for k in ("yt_queries", "skate_queries", "search_queries")
        ):
            render_rich_cards(
                msg.get("yt_queries",     []),
                msg.get("skate_queries",  []),
                msg.get("search_queries", []),
            )
        if role == "assistant" and msg.get("visual_result"):
            render_generated_visual(msg["visual_result"])


# =========================
# 📸 🎥 UPLOAD BAR + ATTACHMENT PREVIEW
# Sits just above the chat input, always visible
# =========================
upload_col1, upload_col2, spacer_col = st.columns([2, 2, 5])

with upload_col1:
    st.markdown("<div style='font-size:0.72rem;color:#6a85a8;margin-bottom:3px;'>📸 Photo</div>", unsafe_allow_html=True)
    new_photo = st.file_uploader(
        "photo",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
        key="photo_uploader_main",
        help="Attach a skate photo for Remy",
    )
    if new_photo is not None and new_photo != st.session_state.get("_last_photo"):
        st.session_state._last_photo        = new_photo
        st.session_state.pending_image      = new_photo.read()
        st.session_state.pending_image_name = new_photo.name
        st.session_state.pending_video      = None
        st.session_state.pending_video_name = None
        st.rerun()

with upload_col2:
    st.markdown("<div style='font-size:0.72rem;color:#6a85a8;margin-bottom:3px;'>🎥 Video</div>", unsafe_allow_html=True)
    new_video = st.file_uploader(
        "video",
        type=["mp4", "mov", "avi", "webm", "mkv"],
        label_visibility="collapsed",
        key="video_uploader_main",
        help="Attach a skating video — Remy analyzes your form (max ~20MB)",
    )
    if new_video is not None and new_video != st.session_state.get("_last_video"):
        st.session_state._last_video        = new_video
        st.session_state.pending_video      = new_video.read()
        st.session_state.pending_video_name = new_video.name
        st.session_state.pending_image      = None
        st.session_state.pending_image_name = None
        st.rerun()

# Attachment preview
if st.session_state.pending_image or st.session_state.pending_video:
    prev_col, remove_col = st.columns([9, 1])
    with prev_col:
        if st.session_state.pending_image:
            st.image(
                st.session_state.pending_image,
                width=160,
                caption="📸 Sends with your next message",
            )
        elif st.session_state.pending_video:
            vname = st.session_state.pending_video_name or "video"
            vsize = len(st.session_state.pending_video) / (1024 * 1024)
            st.markdown(
                f"<div style='background:#0c1220;border:1px solid #1a2840;"
                f"border-radius:10px;padding:9px 14px;font-size:0.82rem;color:#6a85a8;'>"
                f"🎥 <strong style='color:#eef4ff;'>{html.escape(vname)}</strong>"
                f" &nbsp;·&nbsp; {vsize:.1f} MB · "
                f"<span style='font-size:0.74rem;'>sends with your next message</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    with remove_col:
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        if st.button("✕", key="remove_attachment_main", help="Remove attachment"):
            st.session_state.pending_image      = None
            st.session_state.pending_image_name = None
            st.session_state.pending_video      = None
            st.session_state.pending_video_name = None
            st.rerun()

# =========================
# ⌨️ CHAT INPUT
# =========================
user_input = st.chat_input("Ask Remy anything about skating...", key="chat_input_main")

# =========================
# ⌨️ INPUT HANDLER
# =========================
triggered_input = None
if st.session_state._quick_prompt:
    triggered_input                = st.session_state._quick_prompt
    st.session_state._quick_prompt = None

final_input = triggered_input or (user_input.strip() if user_input else None)

# Supported video MIME types
_VIDEO_MIME = {
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "avi": "video/x-msvideo",
    "webm": "video/webm",
    "mkv": "video/x-matroska",
}

if final_input:
    img_bytes   = st.session_state.pending_image
    img_name    = st.session_state.pending_image_name
    vid_bytes   = st.session_state.pending_video
    vid_name    = st.session_state.pending_video_name or ""

    user_msg = {"role": "user", "content": final_input}
    if img_bytes:
        user_msg["image"] = img_bytes
    if vid_bytes:
        user_msg["video_name"] = vid_name

    st.session_state.messages.append(user_msg)
    st.session_state.msg_count += 1

    with st.chat_message("user"):
        if img_bytes:
            st.image(img_bytes, width=260)
        if vid_bytes:
            vsize = len(vid_bytes) / (1024 * 1024)
            st.markdown(
                f"<div style='background:#0c1220;border:1px solid #1a2840;"
                f"border-radius:10px;padding:8px 13px;font-size:0.82rem;color:#6a85a8;"
                f"margin-bottom:6px;'>"
                f"🎥 <strong style='color:#eef4ff;'>{html.escape(vid_name)}</strong>"
                f" &nbsp;·&nbsp; {vsize:.1f} MB</div>",
                unsafe_allow_html=True,
            )
        st.markdown(final_input)

    st.session_state.pending_image      = None
    st.session_state.pending_image_name = None
    st.session_state.pending_video      = None
    st.session_state.pending_video_name = None

    try:
        message_parts: list = []

        # ── Image part ──
        if img_bytes:
            try:
                pil_img = Image.open(io.BytesIO(img_bytes))
                fmt     = pil_img.format or "JPEG"
                mime    = f"image/{fmt.lower().replace('jpg', 'jpeg')}"
            except Exception as exc:
                _api_warn("image_decode", exc)
                mime = "image/jpeg"
            message_parts.append({"mime_type": mime, "data": img_bytes})

        # ── Video part — extract frames and send as images ──
        # Gemini interprets individual frames much more reliably than
        # raw video bytes for fast-moving footage like skating.
        if vid_bytes:
            with st.spinner("🎬 Extracting frames from your video..."):
                frames = extract_video_frames(vid_bytes, num_frames=6)

            if frames:
                # Prepend a context note so Remy knows these are video frames
                # Compact note — keeps token overhead low
                frame_note = (
                    f"[VIDEO FRAMES: {len(frames)} frames from '{vid_name}'. "
                    f"Analyze as sequential skating footage: form, posture, "
                    f"foot placement, timing, weight distribution.]"
                )
                message_parts.insert(0, frame_note)
                for frame_bytes in frames:
                    message_parts.append({"mime_type": "image/jpeg", "data": frame_bytes})
                # Show frame count in UI
                st.markdown(
                    f"<div style='font-size:0.72rem;color:#6a85a8;margin-bottom:6px;'>"
                    f"🎬 Extracted {len(frames)} frames from your video for Remy to analyze</div>",
                    unsafe_allow_html=True,
                )
            else:
                # Frame extraction failed — fall back to raw video
                _api_warn("video_frames", Exception("No frames extracted, falling back to raw video"))
                ext      = vid_name.rsplit(".", 1)[-1].lower() if "." in vid_name else "mp4"
                vid_mime = _VIDEO_MIME.get(ext, "video/mp4")
                message_parts.append({"mime_type": vid_mime, "data": vid_bytes})
                st.markdown(
                    "<div style='font-size:0.72rem;color:#ffb830;margin-bottom:6px;'>"
                    "⚠️ Could not extract frames — sending raw video instead</div>",
                    unsafe_allow_html=True,
                )

        # ── Trusted-source pre-fetch ──
        # Search BEFORE sending to Gemini so the results are baked into the prompt
        # and Remy can reference them while generating his answer.
        enriched_input = final_input
        search_status  = None

        if needs_trusted_search(final_input) and cse_ok:
            with st.spinner("🔎 Remy is checking trusted skating sources..."):
                live_context = build_search_context(final_input)
            if live_context:
                enriched_input = (
                    f"{live_context}\n\n"
                    f"---\n"
                    f"Now respond to the user's message, using the source data above "
                    f"where relevant. User said: {final_input}"
                )
                search_status = final_input

        elif needs_trusted_search(final_input) and not cse_ok:
            st.markdown("""
            <div style='background:#101828;border:1px solid #1a2840;border-radius:10px;
                        padding:10px 14px;margin:6px 0;font-size:0.78rem;color:#6a85a8;'>
                🔎 <strong style='color:#ffb830;'>Trusted source search not active</strong> —
                add <code>GOOGLE_CSE_KEY</code> + <code>GOOGLE_CSE_CX</code> to your .env.
                Answering from training knowledge for now.
            </div>
            """, unsafe_allow_html=True)

        message_parts.append(enriched_input)

        # ── Trim conversation history to avoid bloating the context window ──
        # Gemini's chat object carries the full history each turn.
        # If the session has grown long, prune it to the last N turns
        # so we don't push the prompt+output over the token limit.
        _MAX_HISTORY_TURNS = 10  # each turn = 1 user + 1 assistant message
        history = st.session_state.chat.history
        if len(history) > _MAX_HISTORY_TURNS * 2:
            # Keep system-like first message if present, then last N turns
            st.session_state.chat.history = history[-(_MAX_HISTORY_TURNS * 2):]

        # ── Stream response ──
        # Use stream=True for live typing effect.
        # We accumulate text from chunks ourselves so we are never
        # dependent on re-reading the consumed iterator afterward.
        response      = st.session_state.chat.send_message(message_parts, stream=True)
        full_response = ""
        resolved      = None   # will hold the resolved response after streaming
        visual_result = None

        with st.chat_message("assistant", avatar="🛼"):
            if search_status:
                st.markdown(
                    f"<div style='font-size:0.72rem;color:#6a85a8;margin-bottom:8px;'>"
                    f"🔎 Checked trusted skating sources for: <em>{_esc(search_status, 80)}</em></div>",
                    unsafe_allow_html=True,
                )
            placeholder = st.empty()

            # Consume the stream — capture text from each chunk directly
            try:
                for chunk in response:
                    text = _safe_chunk_text(chunk)
                    if text:
                        full_response += text
                        placeholder.markdown(full_response + "▌")
            except ValueError:
                # Stream ended early (finish_reason=2 max_tokens, etc.)
                # full_response contains whatever arrived before cutoff
                pass

            # After the iterator is exhausted, resolve() consolidates all
            # chunks into a single final response object — safe to call even
            # after the stream is consumed, and does NOT re-request anything.
            try:
                response.resolve()
                resolved = response
            except Exception as exc:
                _api_warn("stream_resolve", exc)

            # If we got nothing from streaming, try the resolved object
            if not full_response.strip() and resolved is not None:
                full_response = _safe_response_text(resolved)

            # Final fallback so the UI never shows a blank bubble
            if not full_response.strip():
                full_response = (
                    "I got cut off there — my response was a bit long. "
                    "Could you ask me again, or break it into a smaller question? "
                    "I'm still here. 🛼"
                )

            placeholder.markdown("")  # clear cursor

            # Log finish_reason / candidate / parts metadata for debugging
            try:
                _log_response_meta(resolved or response, "stream_end")
            except Exception:
                pass

            # ── Extract tags, render clean text + cards ──
            clean_text, yt_queries, skate_queries, search_queries = extract_tags(full_response)

            # 🔥 Auto-trigger image generation if Remy created a visual block
            if "Image Prompt" in full_response or "VISUAL COACHING" in full_response:
                st.session_state.force_generate_visual = True

            placeholder.markdown(clean_text)

            # If Remy embedded [SEARCH:] tags, run those searches now and show
            # source cards below his answer (second-pass enrichment for display).
            render_rich_cards(yt_queries, skate_queries, search_queries)

            # ── Generated Visuals ──
            should_generate_visual = (
                should_trigger_generated_visual(final_input)
                or st.session_state.force_generate_visual
            )

            if should_generate_visual:
                visual_result = generate_visual(
                    user_message=final_input,
                    skill_level=st.session_state.skill_level,
                    coaching_summary=clean_text,
                )
                render_generated_visual(visual_result)
                st.session_state.force_generate_visual = False

        st.session_state.messages.append({
            "role":           "assistant",
            "content":        clean_text,
            "yt_queries":     yt_queries,
            "skate_queries":  skate_queries,
            "search_queries": search_queries,
            "visual_result":  visual_result,
        })

    except Exception as exc:
        st.error(f"Remy hit a snag — {type(exc).__name__}: {exc}")