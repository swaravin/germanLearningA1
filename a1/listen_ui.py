"""Shared Listen-toolbar button styling (speech + image actions)."""

from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

LISTEN_TOOLBAR_BTN_CSS = """
.a1-listen-row {
    display: flex;
    gap: 0.5rem;
    align-items: stretch;
    width: 100%;
    margin: 0;
    padding: 0;
}
.a1-speech-btn {
    flex: 1 1 0;
    min-width: 0;
    box-sizing: border-box;
    padding: 0.55rem 0.5rem;
    cursor: pointer;
    border-radius: 0.5rem;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: clamp(0.75rem, 3vw, 0.95rem);
    line-height: 1.2;
    white-space: normal;
    text-align: center;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.a1-speech-primary {
    background: #f4f8f6;
    border: 1.5px solid #0f3d2e;
    color: #0f3d2e;
}
.a1-speech-secondary {
    background: #fff;
    border: 1.5px solid #888;
    color: #333;
    font-size: clamp(0.72rem, 2.8vw, 0.85rem);
}
@media (max-width: 640px) {
    .a1-listen-row {
        flex-wrap: wrap;
    }
    .a1-speech-btn {
        flex: 1 1 calc(50% - 0.25rem);
        min-height: 44px;
    }
}
@media (prefers-color-scheme: dark) {
    .a1-speech-primary {
        background: #1e3a5f;
        border-color: #7eb8e8;
        color: #e2e8f0;
    }
    .a1-speech-secondary {
        background: #243044;
        border-color: #475569;
        color: #e2e8f0;
    }
}
"""

LISTEN_ROW_HEIGHT = 44

# Legacy CSS kept for saved-audio fallback columns (if any)
LISTEN_ST_BUTTON_CSS = ""
LISTEN_ST_BUTTON_DARK_CSS = ""


def handle_load_image_query() -> bool:
    """Load image when the Listen toolbar sets ?load_img=<word_id>. Returns True if handled."""
    raw = st.query_params.get("load_img")
    if not raw:
        return False
    try:
        word_id = int(raw)
    except ValueError:
        st.query_params.pop("load_img", None)
        return False

    from a1.images import ensure_image

    deck = st.session_state.get("deck", [])
    word = next((w for w in deck if w.id == word_id), None)
    st.query_params.pop("load_img", None)
    if word:
        ensure_image(word.id, word.german, word.english, word.image_query, section=word.section)
        st.rerun()
    return True


def render_listen_toolbar(
    *,
    word_id: int,
    german_text: str,
    english_text: str,
    de_rate: float = 0.78,
    en_rate: float = 1.0,
) -> None:
    """One aligned row: German · English · Load image."""
    de_js = json.dumps(german_text)
    en_js = json.dumps(english_text)
    word_id_js = json.dumps(word_id)
    de_rate_js = json.dumps(de_rate)
    en_rate_js = json.dumps(en_rate)

    components.html(
        f"""
        <style>
        html, body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: transparent;
        }}
        {LISTEN_TOOLBAR_BTN_CSS}
        </style>
        <div class="a1-listen-row">
          <button id="a1_listen_de" type="button" class="a1-speech-btn a1-speech-primary">🔊 German word</button>
          <button id="a1_listen_en" type="button" class="a1-speech-btn a1-speech-primary">🔊 English meaning</button>
          <button id="a1_listen_img" type="button" class="a1-speech-btn a1-speech-primary">🖼 Load image</button>
        </div>
        <script>
        (function() {{
            function pickVoice(langCode) {{
                const synth = window.speechSynthesis;
                if (!synth) return null;
                const voices = synth.getVoices();
                const short = langCode.slice(0, 2);
                return voices.find(v => v.lang && v.lang.startsWith(short))
                    || voices.find(v => v.lang && v.lang.includes(short))
                    || null;
            }}

            function speak(text, lang, rate) {{
                const synth = window.speechSynthesis;
                if (!synth) return;
                synth.cancel();
                const utter = new SpeechSynthesisUtterance(text);
                utter.lang = lang;
                utter.rate = rate;
                const voice = pickVoice(lang);
                if (voice) utter.voice = voice;
                synth.speak(utter);
            }}

            document.getElementById("a1_listen_de").addEventListener("click", () => {{
                speak({de_js}, "de-DE", {de_rate_js});
            }});
            document.getElementById("a1_listen_en").addEventListener("click", () => {{
                speak({en_js}, "en-US", {en_rate_js});
            }});
            document.getElementById("a1_listen_img").addEventListener("click", () => {{
                try {{
                    const url = new URL(window.parent.location.href);
                    url.searchParams.set("load_img", String({word_id_js}));
                    window.parent.location.href = url.toString();
                }} catch (e) {{
                    window.parent.location.search = "load_img=" + encodeURIComponent(String({word_id_js}));
                }}
            }});

            if (window.speechSynthesis) {{
                window.speechSynthesis.onvoiceschanged = () => {{ pickVoice("de-DE"); }};
            }}
        }})();
        </script>
        """,
        height=LISTEN_ROW_HEIGHT,
    )
