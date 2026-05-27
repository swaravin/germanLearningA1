from __future__ import annotations

import streamlit as st

from a1.audio import get_word_audio_path
from a1.browser_audio import online_tts_preview, speak_button
from a1.browser_lookup import fetch_audio_to_session


def render_word_audio(
    label: str,
    word_id: int,
    kind: str,
    text: str,
    *,
    lang: str,
    button_id: str,
    rate: float = 1.0,
) -> None:
    """Play saved audio for a word, or fall back to browser speech."""
    path = get_word_audio_path(word_id, kind)
    if path:
        st.caption(label)
        st.audio(str(path))
    else:
        speak_button(label, text, lang=lang, button_id=button_id, rate=rate)


def _audio_slot(state_key: str, ext_key: str) -> tuple[bytes | None, str | None]:
    data = st.session_state.get(state_key)
    ext = st.session_state.get(ext_key)
    if isinstance(data, bytes) and data:
        return data, ext or ".webm"
    return None, None


def render_add_card_audio(label: str, text: str, lang: str, *, state_key: str, ext_key: str, rec_key: str) -> None:
    """Record/upload audio or fetch online for a new card."""
    st.markdown(f"**{label}**")
    lang_code = "de" if lang.startswith("de") else "en"

    btn_find, btn_preview = st.columns(2)
    with btn_find:
        if st.button("Find online", key=f"find_{state_key}", use_container_width=True):
            fetch_audio_to_session(text, lang_code, state_key=state_key, ext_key=ext_key)

    with btn_preview:
        if text.strip():
            online_tts_preview(
                "Listen",
                text,
                lang=lang,
                button_id=f"preview_{state_key}",
                rate=0.78 if lang_code == "de" else 1.0,
            )

    data, ext = _audio_slot(state_key, ext_key)
    if data:
        st.audio(data)
        if st.button("Remove saved clip", key=f"clear_{state_key}", use_container_width=True):
            st.session_state.pop(state_key, None)
            st.session_state.pop(ext_key, None)
            st.rerun()

    recording = st.audio_input(
        f"Record or upload {label.lower()}",
        key=rec_key,
    )
    if recording is not None:
        from a1.audio import ext_from_mime

        st.session_state[state_key] = recording.getvalue()
        st.session_state[ext_key] = ext_from_mime(recording.type)
