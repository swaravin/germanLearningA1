from __future__ import annotations

import html
import json

import streamlit.components.v1 as components


def speak_button(
    label: str,
    text: str,
    *,
    lang: str,
    button_id: str,
    rate: float = 1.0,
) -> None:
    """Play speech in the browser using the Web Speech API (no server network)."""
    if not text.strip():
        return

    _speech_button_html(label, text, lang=lang, button_id=button_id, rate=rate, variant="primary")


def online_tts_preview(
    label: str,
    text: str,
    *,
    lang: str,
    button_id: str,
    rate: float = 1.0,
) -> None:
    """Listen using the browser's built-in voice (works offline, no Google fetch)."""
    if not text.strip():
        return

    _speech_button_html(label, text, lang=lang, button_id=button_id, rate=rate, variant="secondary")


def _speech_button_html(
    label: str,
    text: str,
    *,
    lang: str,
    button_id: str,
    rate: float,
    variant: str,
) -> None:
    text_js = json.dumps(text)
    lang_js = json.dumps(lang)
    label_html = html.escape(label)
    button_id_js = json.dumps(button_id)
    rate_js = json.dumps(rate)

    if variant == "primary":
        btn_class = "a1-speech-btn a1-speech-primary"
    else:
        btn_class = "a1-speech-btn a1-speech-secondary"

    components.html(
        f"""
        <style>
        .a1-speech-btn {{
            width: 100%;
            padding: 0.55rem 0.75rem;
            cursor: pointer;
            border-radius: 0.5rem;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
        }}
        .a1-speech-primary {{
            background: #f4f8f6;
            border: 1.5px solid #0f3d2e;
            color: #0f3d2e;
            font-size: 0.95rem;
        }}
        .a1-speech-secondary {{
            background: #fff;
            border: 1.5px solid #888;
            color: #333;
            font-size: 0.85rem;
        }}
        .a1-speech-msg {{ font-size: 0.75rem; color: #666; margin: 0.35rem 0 0; }}
        @media (prefers-color-scheme: dark) {{
            .a1-speech-primary {{
                background: #1e3a5f;
                border-color: #7eb8e8;
                color: #e2e8f0;
            }}
            .a1-speech-secondary {{
                background: #243044;
                border-color: #475569;
                color: #e2e8f0;
            }}
            .a1-speech-msg {{ color: #94a3b8; }}
        }}
        </style>
        <button id="{button_id}" type="button" class="{btn_class}">{label_html}</button>
        <p id="{button_id}_msg" class="a1-speech-msg"></p>
        <script>
        (function() {{
            const btn = document.getElementById({button_id_js});
            const msg = document.getElementById({button_id_js} + "_msg");
            if (!btn) return;

            function pickVoice(langCode) {{
                const synth = window.speechSynthesis;
                if (!synth) return null;
                const voices = synth.getVoices();
                const short = langCode.slice(0, 2);
                return voices.find(v => v.lang && v.lang.startsWith(short))
                    || voices.find(v => v.lang && v.lang.includes(short))
                    || null;
            }}

            btn.addEventListener("click", () => {{
                const synth = window.speechSynthesis;
                if (!synth) {{
                    msg.textContent = "Speech not supported in this browser.";
                    return;
                }}
                synth.cancel();
                const utter = new SpeechSynthesisUtterance({text_js});
                utter.lang = {lang_js};
                utter.rate = {rate_js};
                const voice = pickVoice({lang_js});
                if (voice) utter.voice = voice;
                utter.onstart = () => {{ msg.textContent = "Playing…"; }};
                utter.onend = () => {{ msg.textContent = "Use Record below to save your own clip."; }};
                utter.onerror = () => {{ msg.textContent = "Could not play — try Record/upload."; }};
                synth.speak(utter);
            }});

            if (window.speechSynthesis) {{
                window.speechSynthesis.onvoiceschanged = () => {{ pickVoice({lang_js}); }};
            }}
        }})();
        </script>
        """,
        height=68,
    )
