"""
German flashcard app (A1, A2, …) — run: streamlit run app.py
"""

from __future__ import annotations

import html
import streamlit as st

from a1.audio import delete_word_audio, get_word_audio_path, save_word_audio
from a1.browser_lookup import apply_sentences, apply_translation, continue_pending_jobs, fetch_audio_to_session
from a1.word_audio import render_add_card_audio, render_word_audio
from a1.config import CUSTOM_SECTION, FULL_AUDIO_DIR, ROOT
from a1.levels import CEFRLevel, all_levels, default_level_id, ensure_level_layout, get_level as get_cefr_meta, level_ids, vocabulary_path
from a1.full_course import (
    append_word_to_courses,
    clip_words_available,
    course_audio_path,
    courses_missing,
    extended_course_status,
    ffmpeg_available,
    invalidate_extended_courses,
    rebuild_plus_custom_courses,
)
from a1.images import ensure_image, image_path, placeholder_svg
from a1.listen_ui import handle_load_image_query, render_listen_toolbar
from a1.articles import (
    article_for_german,
    default_example_sentences,
    german_de_speech,
    german_with_article,
    german_with_article_word,
    pronunciation_display,
)
from a1.comfort import (
    COMFORT_LABELS,
    COMFORT_FILTERS,
    comfort_filter_label,
    comfort_revision,
    comfort_stats,
    count_by_comfort_filter,
    effective_level,
    explain_empty_comfort_filter,
    filter_words_by_comfort,
    get_level as get_comfort_level,
    index_of_word,
    normalize_comfort_filter,
    set_level as set_comfort_level,
    weighted_pick,
    weighted_shuffle_deck,
)
from a1.vocab import (
    Word,
    add_custom_word,
    delete_custom_word,
    english_short,
    filter_words,
    get_custom_word,
    is_custom_word,
    load_all_vocabulary,
    load_custom_vocabulary,
    search_words,
    sections,
    shuffle_deck,
    update_custom_word,
    vocabulary_revision,
)

FRONT_MODES = ("German", "English", "German + English")
ARTICLE_OPTIONS = ["Auto", "der", "die", "das", "—"]
FONT_SIZE_OPTIONS = {
    "Small": 0.85,
    "Normal": 1.0,
    "Large": 1.25,
    "X-Large": 1.5,
    "XX-Large": 1.75,
}

st.set_page_config(
    page_title="German Learn",
    page_icon="🇩🇪",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """
    <style>
    .flash-de { font-weight: 700; color: #0f3d2e; text-align: center; }
    .flash-article { color: #6b8f84; font-weight: 600; }
    .flash-en { color: #333; text-align: center; }
    .flash-pron { color: #666; text-align: center; }
    .flash-card {
        padding: 0;
        margin: 0;
    }
    .flash-card-body {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        overflow: hidden;
        box-sizing: border-box;
    }
    .flash-card-caption {
        text-align: center;
        color: #666;
        overflow-y: auto;
        box-sizing: border-box;
    }
    .flash-de, .flash-en, .flash-pron {
        margin: 0.15em 0;
        width: 100%;
    }
    .flash-card-label {
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #888;
        margin: 0;
        padding-top: 0.15rem;
        text-align: center;
    }
    /* Card shell */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker) {
        background: #ffffff;
        border: 2px solid #0f3d2e !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 14px rgba(15, 61, 46, 0.08);
        padding: 0.75rem 1rem 1.25rem !important;
    }
    /* Prev / flip / next — see flash-card nav block at end of stylesheet */
    div[data-testid="stSidebar"] { background: #f4f6f4; }

    /* Default Streamlit buttons (light) — descendant selector for Streamlit 1.57+ */
    .stApp div[data-testid="stButton"] button[kind="secondary"],
    .stApp div[data-testid="stButton"] button:not([kind="primary"]) {
        background: #ffffff !important;
        color: #0f3d2e !important;
        border: 1.5px solid #c5d5ce !important;
        border-radius: 10px !important;
    }
    .stApp div[data-testid="stButton"] button[kind="secondary"] p,
    .stApp div[data-testid="stButton"] button:not([kind="primary"]) p,
    .stApp div[data-testid="stButton"] button[kind="secondary"] span,
    .stApp div[data-testid="stButton"] button:not([kind="primary"]) span {
        color: #0f3d2e !important;
    }
    .stApp div[data-testid="stButton"] button[kind="secondary"]:hover,
    .stApp div[data-testid="stButton"] button:not([kind="primary"]):hover {
        background: #f4f8f6 !important;
        border-color: #0f3d2e !important;
        color: #0f3d2e !important;
    }
    .stApp div[data-testid="stButton"] button[kind="primary"] {
        background: #0f3d2e !important;
        color: #ffffff !important;
        border: 1.5px solid #0f3d2e !important;
        border-radius: 10px !important;
    }
    .stApp div[data-testid="stButton"] button[kind="primary"] p,
    .stApp div[data-testid="stButton"] button[kind="primary"] span {
        color: #ffffff !important;
    }
    .stApp div[data-testid="stButton"] button[kind="primary"]:hover {
        background: #1a5c45 !important;
        border-color: #1a5c45 !important;
    }
    [data-testid="stSidebar"] div[data-testid="stButton"] button {
        background: #ffffff !important;
        color: #0f3d2e !important;
        border: 1px solid #c5d5ce !important;
    }
    [data-testid="stSidebar"] div[data-testid="stButton"] button p,
    [data-testid="stSidebar"] div[data-testid="stButton"] button span {
        color: #0f3d2e !important;
    }

    /* Flashcard ◀ Prev / Flip / Next ▶ — inside bordered card shell */
    .stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker)
    [data-testid="stButton"] button {
        min-height: 44px !important;
        border-radius: 10px !important;
        background: #e8f0ec !important;
        border: 1.5px solid #0f3d2e !important;
        color: #0f3d2e !important;
        box-shadow: 0 2px 6px rgba(15, 61, 46, 0.12) !important;
    }
    .stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker)
    [data-testid="stButton"] button * {
        color: #0f3d2e !important;
    }
    .stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker)
    [data-testid="stButton"] button:hover {
        background: #d4e4dc !important;
        border-color: #0f3d2e !important;
    }

    /* System light / dark — follows iOS / macOS appearance */
    html { color-scheme: light dark; }

    @media (prefers-color-scheme: dark) {
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background-color: #0e1117 !important;
            color: #e2e8f0 !important;
        }
        [data-testid="stHeader"] { background: transparent !important; }
        [data-testid="stSidebar"] {
            background: #1a1f2e !important;
            border-right: 1px solid #2d3748 !important;
        }
        [data-testid="stSidebar"] * { color: #e2e8f0; }
        .flash-de { color: #a8e6cf !important; }
        .flash-article { color: #7eb8e8 !important; }
        .flash-en { color: #e2e8f0 !important; }
        .flash-pron, .flash-card-caption, .flash-card-label { color: #94a3b8 !important; }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker) {
            background: #1e293b !important;
            border-color: #4ade80 !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35) !important;
        }
        .stApp div[data-testid="stButton"] button[kind="secondary"],
        .stApp div[data-testid="stButton"] button:not([kind="primary"]) {
            background: #243044 !important;
            color: #e2e8f0 !important;
            border-color: #475569 !important;
        }
        .stApp div[data-testid="stButton"] button[kind="secondary"] p,
        .stApp div[data-testid="stButton"] button:not([kind="primary"]) p,
        .stApp div[data-testid="stButton"] button[kind="secondary"] span,
        .stApp div[data-testid="stButton"] button:not([kind="primary"]) span {
            color: #e2e8f0 !important;
        }
        .stApp div[data-testid="stButton"] button[kind="secondary"]:hover,
        .stApp div[data-testid="stButton"] button:not([kind="primary"]):hover {
            background: #2d3a4f !important;
            border-color: #7eb8e8 !important;
            color: #ffffff !important;
        }
        .stApp div[data-testid="stButton"] button[kind="primary"] {
            background: #7eb8e8 !important;
            color: #0b1220 !important;
            border-color: #7eb8e8 !important;
        }
        .stApp div[data-testid="stButton"] button[kind="primary"] p,
        .stApp div[data-testid="stButton"] button[kind="primary"] span {
            color: #0b1220 !important;
        }
        .stApp div[data-testid="stButton"] button[kind="primary"]:hover {
            background: #9ccbf0 !important;
            border-color: #9ccbf0 !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] button {
            background: #243044 !important;
            color: #e2e8f0 !important;
            border-color: #475569 !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] button p,
        [data-testid="stSidebar"] div[data-testid="stButton"] button span {
            color: #e2e8f0 !important;
        }
        /* Flashcard nav — accent buttons, readable on dark card */
        .stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker)
        [data-testid="stButton"] button {
            background: #1e3a5f !important;
            border-color: #7eb8e8 !important;
            color: #ffffff !important;
        }
        .stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker)
        [data-testid="stButton"] button * {
            color: #ffffff !important;
        }
        .stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker)
        [data-testid="stButton"] button:hover {
            background: #25466d !important;
            border-color: #9ccbf0 !important;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background-color: #1e293b !important;
            color: #e2e8f0 !important;
            border-color: #334155 !important;
        }
        [data-testid="stCheckbox"] label span {
            color: #e2e8f0 !important;
        }
        /* Main area — titles, captions, radio labels (dark-on-dark fix) */
        [data-testid="stMain"] h1,
        [data-testid="stMain"] h2,
        [data-testid="stMain"] h3,
        [data-testid="stMain"] label,
        [data-testid="stMain"] [data-testid="stMarkdown"] p,
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stMain"] [data-testid="stCaption"],
        [data-testid="stMain"] [data-testid="stWidgetLabel"] p,
        [data-testid="stMain"] [data-testid="stRadio"] label span,
        [data-testid="stMain"] [data-testid="stRadio"] label p,
        [data-testid="stMain"] [data-testid="stRadio"] legend {
            color: #e2e8f0 !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label span,
        [data-testid="stSidebar"] [data-testid="stRadio"] label p,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            color: #e2e8f0 !important;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background-color: #1e293b !important;
            color: #e2e8f0 !important;
            border-color: #475569 !important;
        }
    }

    /* ── Responsive layout (phone, tablet, desktop) ── */
    .flashcard-layout {
        width: 100%;
        max-width: 680px;
        margin: 0 auto;
        padding: 0 0.25rem;
    }

    .stApp .block-container {
        max-width: 1200px;
        padding-top: 1.25rem;
        padding-bottom: 2rem;
    }

    .stApp [data-testid="stImage"] img {
        max-height: min(42vh, 320px);
        width: auto !important;
        margin: 0 auto;
        object-fit: contain;
    }

    @media (max-width: 900px) {
        .stApp .block-container {
            max-width: 100%;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .flashcard-layout {
            max-width: 100%;
        }
    }

    @media (max-width: 640px) {
        .stApp .block-container {
            padding-left: 0.75rem;
            padding-right: 0.75rem;
            padding-top: 0.75rem;
        }
        [data-testid="stHeader"] {
            background: transparent !important;
        }
        [data-testid="stToolbar"] {
            display: none !important;
        }
        .flash-de {
            font-size: clamp(1.35rem, 7vw, 2rem) !important;
            word-break: break-word;
        }
        .flash-en {
            font-size: clamp(1.05rem, 4.5vw, 1.45rem) !important;
            word-break: break-word;
        }
        .flash-pron, .flash-card-caption {
            font-size: clamp(0.82rem, 3.5vw, 1rem) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker) {
            padding: 0.5rem 0.65rem 0.85rem !important;
        }
        .stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker)
        [data-testid="stButton"] button {
            min-height: 48px !important;
            font-size: 0.92rem !important;
        }
        [data-testid="column"] [data-testid="stButton"] button {
            padding-left: 0.25rem !important;
            padding-right: 0.25rem !important;
        }
    }

    @media (max-width: 380px) {
        .stApp .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _cefr() -> str:
    return st.session_state.get("cefr_level", default_level_id())


def _cefr_meta() -> CEFRLevel:
    return get_cefr_meta(_cefr())


def _cefr_level_label(level_id: str) -> str:
    meta = get_cefr_meta(level_id)
    return f"{meta.label} — {meta.subtitle}" if meta.subtitle else meta.label


def _ensure_cefr_session(level_ids: list[str]) -> None:
    if "cefr_level" not in st.session_state or st.session_state.cefr_level not in level_ids:
        st.session_state.cefr_level = default_level_id()


def _switch_cefr_level(new_level: str) -> None:
    if new_level == st.session_state.get("cefr_level"):
        return
    st.session_state.cefr_level = new_level
    st.session_state.deck_filter_key = None
    st.session_state.pop("deck", None)
    st.session_state.card_i = 0
    st.session_state.card_history = []
    st.rerun()


def _comfort_practice_key() -> str:
    return f"comfort_practice_{_cefr()}"


def _section_key() -> str:
    return f"section_{_cefr()}"


def _images_only_key() -> str:
    return f"images_only_{_cefr()}"


def _deck_fingerprint(words: list[Word]) -> tuple[int, ...]:
    return tuple(sorted(w.id for w in words))


def _deck_matches_filter(deck: list[Word], filtered: list[Word]) -> bool:
    if not deck or not filtered:
        return not deck and not filtered
    return _deck_fingerprint(deck) == _deck_fingerprint(filtered)


def _deck_filter_key(
    deck: list[Word],
    *,
    cefr_level: str,
    vocab_rev: tuple[float, float],
) -> tuple:
    return (
        cefr_level,
        vocab_rev,
        normalize_comfort_filter(st.session_state.get(_comfort_practice_key(), "all")),
        comfort_revision(cefr_level),
        bool(st.session_state.get("comfort_weighted", True)),
        _deck_fingerprint(deck),
    )


def _build_deck_from_filtered(filtered: list[Word], cefr_level: str) -> list[Word]:
    if st.session_state.get("comfort_weighted", True):
        return weighted_shuffle_deck(filtered, cefr_level)
    return list(filtered)


def _sanitize_filter_session() -> None:
    """Fix corrupted comfort-filter session values from older app versions."""
    st.session_state.pop("comfort_filter", None)
    valid = {k for k, _ in COMFORT_FILTERS}
    for level_id in level_ids():
        practice_key = f"comfort_practice_{level_id}"
        if practice_key not in st.session_state:
            continue
        normalized = normalize_comfort_filter(st.session_state[practice_key])
        if normalized not in valid:
            st.session_state[practice_key] = "all"
        else:
            st.session_state[practice_key] = normalized


def render_cefr_level_picker_sidebar() -> None:
    """CEFR level dropdown at top of sidebar."""
    ensure_level_layout()
    levels = all_levels()
    level_ids = [lv.id for lv in levels]
    _ensure_cefr_session(level_ids)
    prev = st.session_state.cefr_level
    choice = st.sidebar.selectbox(
        "Word list level",
        options=level_ids,
        index=level_ids.index(prev),
        format_func=_cefr_level_label,
    )
    if choice != prev:
        _switch_cefr_level(choice)
    st.sidebar.divider()


def load_app_vocabulary(level_id: str | None = None) -> list[Word]:
    """Load built-in + custom cards for the selected CEFR level."""
    level_id = level_id or _cefr()
    ensure_level_layout()
    path = vocabulary_path(level_id)
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        st.error(
            f"Missing word list for **{level_id.upper()}** at `{path}`.\n\n"
            f"For A1: `python scripts/export_vocabulary.py`\n"
            f"For A2: `python scripts/seed_a2_vocabulary.py`\n"
            f"For C1: `python scripts/seed_c1_vocabulary.py`"
        )
        st.stop()
    words = load_all_vocabulary(level_id)
    if not words:
        st.error(f"No words in {path}. Run the export/seed script for this level.")
        st.stop()
    return words


def _article_from_choice(choice: str) -> str:
    if choice == "—":
        return "-"
    if choice in ("der", "die", "das"):
        return choice
    return ""


def _article_select_value(article: str) -> str:
    if article in ("der", "die", "das"):
        return article
    return "Auto"


def inject_card_font_css(scale: float) -> None:
    body_h = int(200 * scale)
    caption_h = int(52 * scale)
    shell_min = int(320 * scale + 88)
    st.markdown(
        f"""
        <style>
        .flash-de {{
            font-size: {2.4 * scale:.2f}rem !important;
            line-height: 1.2 !important;
        }}
        .flash-en {{
            font-size: {1.5 * scale:.2f}rem !important;
            line-height: 1.25 !important;
        }}
        .flash-pron {{
            font-size: {1.0 * scale:.2f}rem !important;
            line-height: 1.3 !important;
        }}
        .flash-card-label {{
            font-size: {0.75 * scale:.2f}rem !important;
            min-height: {1.5 * scale:.2f}rem !important;
        }}
        .flash-card-body {{
            height: {body_h}px !important;
            min-height: {body_h}px !important;
            max-height: {body_h}px !important;
            padding: 0.35rem 0.5rem !important;
        }}
        .flash-card-caption {{
            height: {caption_h}px !important;
            min-height: {caption_h}px !important;
            max-height: {caption_h}px !important;
            font-size: {0.85 * scale:.2f}rem !important;
            line-height: 1.35 !important;
            padding: 0.35rem 0.5rem 0 !important;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker) {{
            min-height: {shell_min}px !important;
        }}
        @media (max-width: 640px) {{
            .flash-card-body {{
                height: auto !important;
                min-height: {max(120, int(body_h * 0.75))}px !important;
                max-height: none !important;
            }}
            .flash-card-caption {{
                height: auto !important;
                min-height: {max(40, int(caption_h * 0.85))}px !important;
                max-height: none !important;
            }}
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.flash-card-marker) {{
                min-height: auto !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state(deck: list[Word], *, vocab_rev: tuple[float, float], cefr_level: str) -> None:
    key = _deck_filter_key(deck, cefr_level=cefr_level, vocab_rev=vocab_rev)
    session_deck: list[Word] = st.session_state.get("deck") or []
    needs_rebuild = (
        st.session_state.get("deck_filter_key") != key
        or not session_deck
        or not _deck_matches_filter(session_deck, deck)
    )
    if needs_rebuild:
        st.session_state.deck = _build_deck_from_filtered(deck, cefr_level)
        st.session_state.deck_filter_key = key
        st.session_state.card_i = 0
        st.session_state.flipped = False
        st.session_state.card_history = []
    elif st.session_state.deck:
        st.session_state.card_i = st.session_state.card_i % len(st.session_state.deck)
    if "card_history" not in st.session_state:
        st.session_state.card_history = []
    if "comfort_weighted" not in st.session_state:
        st.session_state.comfort_weighted = True


def _push_card_history(word_id: int) -> None:
    history: list[int] = st.session_state.get("card_history", [])
    if history and history[-1] == word_id:
        return
    history.append(word_id)
    st.session_state.card_history = history[-80:]


def _go_to_word(word_id: int) -> None:
    deck: list[Word] = st.session_state.deck
    st.session_state.card_i = index_of_word(deck, word_id)
    st.session_state.flipped = False


def _go_next_card() -> None:
    deck: list[Word] = st.session_state.deck
    if not deck:
        return
    current = deck[st.session_state.card_i % len(deck)]
    _push_card_history(current.id)
    if st.session_state.get("comfort_weighted", True):
        nxt = weighted_pick(
            deck,
            exclude_id=current.id if len(deck) > 1 else None,
            cefr_level=_cefr(),
        )
        if nxt:
            _go_to_word(nxt.id)
            return
    st.session_state.card_i = (st.session_state.card_i + 1) % len(deck)
    st.session_state.flipped = False


def _go_prev_card() -> None:
    history: list[int] = st.session_state.get("card_history", [])
    if history:
        prev_id = history.pop()
        st.session_state.card_history = history
        _go_to_word(prev_id)
        return
    deck: list[Word] = st.session_state.deck
    if deck:
        st.session_state.card_i = (st.session_state.card_i - 1) % len(deck)
        st.session_state.flipped = False


def _go_random_card() -> None:
    deck: list[Word] = st.session_state.deck
    if not deck:
        return
    current = deck[st.session_state.card_i % len(deck)]
    _push_card_history(current.id)
    if st.session_state.get("comfort_weighted", True):
        pick = weighted_pick(
            deck,
            exclude_id=current.id if len(deck) > 1 else None,
            cefr_level=_cefr(),
        )
        if pick:
            _go_to_word(pick.id)
            return
    import random

    idx = st.session_state.card_i
    if len(deck) > 1:
        while (idx := random.randint(0, len(deck) - 1)) == st.session_state.card_i:
            pass
    st.session_state.card_i = idx
    st.session_state.flipped = False


def current_card() -> Word | None:
    deck: list[Word] = st.session_state.deck
    if not deck:
        return None
    i = st.session_state.card_i % len(deck)
    return deck[i]


def _refresh_vocabulary() -> None:
    pass


def _remove_word_from_deck(word_id: int) -> None:
    deck: list[Word] = st.session_state.get("deck", [])
    if not deck:
        return
    idx = next((i for i, w in enumerate(deck) if w.id == word_id), None)
    if idx is None:
        return
    deck.pop(idx)
    st.session_state.deck = deck
    if deck:
        st.session_state.card_i = min(st.session_state.get("card_i", 0), len(deck) - 1)
    else:
        st.session_state.card_i = 0
    st.session_state.flipped = False


def _start_edit_card(word_id: int) -> None:
    st.session_state.edit_word_id = word_id
    st.session_state.mode = "Manage cards"
    for key in (
        "edit_german",
        "edit_english",
        "edit_section",
        "edit_new_section",
        "edit_pron",
        "edit_sent_de",
        "edit_sent_en",
        "edit_de_audio",
        "edit_de_ext",
        "edit_en_audio",
        "edit_en_ext",
    ):
        st.session_state.pop(key, None)
    st.session_state.pop("edit_fields_word_id", None)


def _delete_card(word: Word) -> None:
    if not delete_custom_word(word.id, _cefr()):
        st.error("Could not delete this card.")
        return
    delete_word_audio(word.id)
    _remove_word_from_deck(word.id)
    invalidate_extended_courses()
    _refresh_vocabulary()
    st.session_state.pop(f"confirm_del_{word.id}", None)
    st.session_state.pop("edit_word_id", None)
    st.success(f"Deleted „{word.german}“.")
    st.rerun()


def render_custom_card_actions(word: Word, *, key_prefix: str) -> None:
    """Edit and delete buttons for a user-created card."""
    if not is_custom_word(word.id, _cefr()):
        return
    edit_col, del_col = st.columns(2)
    with edit_col:
        if st.button("Edit", key=f"{key_prefix}_edit_{word.id}", use_container_width=True):
            _start_edit_card(word.id)
            st.rerun()
    with del_col:
        confirm_key = f"confirm_del_{word.id}"
        if st.session_state.get(confirm_key):
            st.warning("Delete permanently?")
            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button("Yes, delete", key=f"{key_prefix}_yes_{word.id}", use_container_width=True):
                    _delete_card(word)
            with no_col:
                if st.button("Cancel", key=f"{key_prefix}_no_{word.id}", use_container_width=True):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
        elif st.button("Delete", key=f"{key_prefix}_del_{word.id}", use_container_width=True):
            st.session_state[confirm_key] = True
            st.rerun()


def _sync_edit_fields(word: Word) -> None:
    if st.session_state.get("edit_fields_word_id") == word.id:
        return
    st.session_state.edit_fields_word_id = word.id
    st.session_state.edit_german = word.german
    st.session_state.edit_english = word.english
    st.session_state.edit_section = word.section
    st.session_state.edit_new_section = ""
    st.session_state.edit_pron = word.pronunciation
    st.session_state.edit_sent_de = word.sentence_de
    st.session_state.edit_sent_en = word.sentence_en
    st.session_state.edit_article = _article_select_value(word.article)


def render_card_edit_form(word: Word, all_words: list[Word]) -> None:
    continue_pending_jobs()
    _sync_edit_fields(word)

    st.header("Edit card")
    st.caption(f"Editing card #{word.id}")

    if st.button("← Back to card list", key="edit_back"):
        st.session_state.pop("edit_word_id", None)
        st.session_state.pop("edit_fields_word_id", None)
        st.rerun()

    section_options = list(dict.fromkeys([CUSTOM_SECTION, word.section, *sections(all_words)]))

    lu_en_col, lu_de_col = st.columns(2)
    with lu_en_col:
        if st.button("Look up English meaning", key="edit_btn_lu_en", use_container_width=True):
            apply_translation(
                st.session_state.get("edit_german", ""),
                "de",
                "en",
                "edit_english",
                "English meaning",
            )
    with lu_de_col:
        if st.button("Look up German word", key="edit_btn_lu_de", use_container_width=True):
            apply_translation(
                st.session_state.get("edit_english", ""),
                "en",
                "de",
                "edit_german",
                "German word",
            )

    st.text_input("German word *", key="edit_german")
    st.text_input("English meaning *", key="edit_english")

    st.selectbox("Section", section_options, key="edit_section")
    st.text_input(
        "Or new section name",
        placeholder="Leave blank to use selection above",
        key="edit_new_section",
    )
    st.selectbox(
        "Article (nouns)",
        ARTICLE_OPTIONS,
        key="edit_article",
        help="Auto picks der/die/das when known. Shown on cards and spoken in audio.",
    )
    st.text_input("Pronunciation (optional)", key="edit_pron")
    if st.button("Look up example sentences", key="edit_btn_lu_sent", use_container_width=True):
        apply_sentences(
            st.session_state.get("edit_german", ""),
            st.session_state.get("edit_english", ""),
            de_key="edit_sent_de",
            en_key="edit_sent_en",
            article=_article_from_choice(st.session_state.get("edit_article", "Auto")),
        )
    st.text_area("German example sentence (optional)", key="edit_sent_de")
    st.text_area("English example sentence (optional)", key="edit_sent_en")

    save_col, cancel_col = st.columns(2)
    with save_col:
        if st.button("Save changes", type="primary", use_container_width=True):
            german = st.session_state.get("edit_german", "")
            english = st.session_state.get("edit_english", "")
            if not str(german).strip() or not str(english).strip():
                st.error("German and English are required.")
                return
            section = str(st.session_state.get("edit_new_section", "")).strip() or st.session_state.get(
                "edit_section", word.section
            )
            try:
                updated = update_custom_word(
                    word.id,
                    german,
                    english,
                    level_id=_cefr(),
                    section=str(section),
                    pronunciation=st.session_state.get("edit_pron", ""),
                    sentence_de=st.session_state.get("edit_sent_de", ""),
                    sentence_en=st.session_state.get("edit_sent_en", ""),
                    article=_article_from_choice(st.session_state.get("edit_article", "Auto")),
                )
            except ValueError as exc:
                st.error(str(exc))
                return

            for kind, state_key, ext_key in (
                ("de", "edit_de_audio", "edit_de_ext"),
                ("en", "edit_en_audio", "edit_en_ext"),
            ):
                data = st.session_state.pop(state_key, None)
                ext = st.session_state.pop(ext_key, None)
                if isinstance(data, bytes) and data:
                    save_word_audio(updated.id, kind, data, ext or ".webm")

            deck: list[Word] = st.session_state.get("deck", [])
            for i, w in enumerate(deck):
                if w.id == updated.id:
                    deck[i] = updated
                    break
            st.session_state.deck = deck

            _refresh_vocabulary()
            invalidate_extended_courses()
            st.session_state.pop("edit_word_id", None)
            st.session_state.pop("edit_fields_word_id", None)
            st.session_state.mode = "Manage cards"
            st.success(f"Updated „{updated.german}“ → {english_short(updated.english)}")
            st.rerun()

    with cancel_col:
        if st.button("Cancel editing", use_container_width=True):
            st.session_state.pop("edit_word_id", None)
            st.session_state.pop("edit_fields_word_id", None)
            st.rerun()

    st.divider()
    st.subheader("Sound")
    st.caption("Replace clips by recording, uploading, or finding online.")
    edit_de_col, edit_en_col = st.columns(2)
    with edit_de_col:
        existing_de = get_word_audio_path(word.id, "de")
        if existing_de and not st.session_state.get("edit_de_audio"):
            st.caption("Current German clip")
            st.audio(str(existing_de))
            if st.button("Remove saved German clip", key=f"clear_disk_de_{word.id}"):
                delete_word_audio(word.id, "de")
                st.rerun()
        render_add_card_audio(
            "German",
            german_with_article(
                st.session_state.get("edit_german", ""),
                article=article_for_german(
                    st.session_state.get("edit_german", ""),
                    stored=_article_from_choice(st.session_state.get("edit_article", "Auto")),
                ),
            ),
            "de-DE",
            state_key="edit_de_audio",
            ext_key="edit_de_ext",
            rec_key="edit_rec_de",
        )
    with edit_en_col:
        existing_en = get_word_audio_path(word.id, "en")
        if existing_en and not st.session_state.get("edit_en_audio"):
            st.caption("Current English clip")
            st.audio(str(existing_en))
            if st.button("Remove saved English clip", key=f"clear_disk_en_{word.id}"):
                delete_word_audio(word.id, "en")
                st.rerun()
        render_add_card_audio(
            "English",
            st.session_state.get("edit_english", ""),
            "en-US",
            state_key="edit_en_audio",
            ext_key="edit_en_ext",
            rec_key="edit_rec_en",
        )


def render_manage_cards(all_words: list[Word]) -> None:
    custom = load_custom_vocabulary(_cefr())
    edit_id = st.session_state.get("edit_word_id")
    if edit_id is not None:
        word = get_custom_word(int(edit_id))
        if word is None:
            st.session_state.pop("edit_word_id", None)
            st.warning("That card no longer exists.")
            st.rerun()
        render_card_edit_form(word, all_words)
        return

    st.header("Manage cards")
    st.caption("Edit or delete cards you added. Built-in deck words cannot be changed here.")

    if not custom:
        st.info("You have no custom cards yet. Use **Add card** to create one.")
        return

    query = st.text_input(
        "Search your cards",
        placeholder="German or English…",
        key="manage_search",
    )
    shown = search_words(custom, query)
    st.caption(f"{len(shown)} custom card{'s' if len(shown) != 1 else ''}")

    for w in shown:
        with st.expander(f"{w.german} — {w.english} · {w.section}"):
            st.write(w.sentence_de)
            st.caption(w.sentence_en)
            render_custom_card_actions(w, key_prefix="manage")


def sidebar(all_words: list[Word]) -> tuple[list[Word], CEFRLevel]:
    ensure_level_layout()
    levels = all_levels()
    level_ids = [lv.id for lv in levels]
    _ensure_cefr_session(level_ids)

    render_cefr_level_picker_sidebar()

    meta = get_cefr_meta(_cefr())
    st.sidebar.title(meta.title)
    if meta.subtitle:
        st.sidebar.caption(meta.subtitle)
    st.sidebar.caption(f"{len(all_words)} words · {len(load_custom_vocabulary(_cefr()))} custom")

    modes = ["Flashcards", "Browse list", "Add card", "Manage cards"]
    if meta.has_feature("mp3_courses"):
        modes.append("Listen — full courses")
    mode_default = st.session_state.get("mode", "Flashcards")
    mode_index = modes.index(mode_default) if mode_default in modes else 0
    mode = st.sidebar.radio("Mode", modes, index=mode_index)
    st.session_state.mode = mode

    sec_list = ["All sections"] + sections(all_words)
    if load_custom_vocabulary(_cefr()) and CUSTOM_SECTION not in sec_list:
        sec_list.append(CUSTOM_SECTION)
    section_index = 0
    if (preferred := st.session_state.pop("preferred_section", None)) and preferred in sec_list:
        section_index = sec_list.index(preferred)
    section = st.sidebar.selectbox(
        "Section",
        sec_list,
        index=section_index,
        key=_section_key(),
    )
    images_only = st.sidebar.checkbox(
        "Only words with pictures",
        value=False,
        key=_images_only_key(),
    )

    section_filtered = filter_words(all_words, section, images_only)
    filtered = section_filtered

    if mode == "Flashcards":
        practice_key = _comfort_practice_key()
        if practice_key not in st.session_state:
            st.session_state[practice_key] = "all"
        elif normalize_comfort_filter(st.session_state[practice_key]) != st.session_state[practice_key]:
            st.session_state[practice_key] = normalize_comfort_filter(st.session_state[practice_key])
        filter_keys = [k for k, _ in COMFORT_FILTERS]

        st.sidebar.selectbox(
            "Practice by comfort",
            options=filter_keys,
            format_func=comfort_filter_label,
            key=practice_key,
            help=(
                "Rate cards with 1–5 below each flashcard, then pick a level here to practice only those words."
            ),
        )
        comfort_filter = normalize_comfort_filter(st.session_state[practice_key])
        filtered = filter_words_by_comfort(section_filtered, comfort_filter, _cefr())

        if "comfort_weighted" not in st.session_state:
            st.session_state.comfort_weighted = True
        st.sidebar.checkbox(
            "Prioritize words I know less",
            value=st.session_state.get("comfort_weighted", True),
            key="comfort_weighted",
            help=(
                "When on, words you rated 1–2 (or not yet rated) appear more often; "
                "words rated 4–5 appear less. Works with any **Practice by comfort** filter."
            ),
        )

        if comfort_filter == "all":
            st.sidebar.caption(f"**{len(section_filtered)}** words match section & pictures")
        else:
            n = len(filtered)
            total = count_by_comfort_filter(all_words, comfort_filter, _cefr())
            if section != "All sections" and n != total:
                st.sidebar.caption(f"**{n}** in deck · **{total}** rated at this level overall")
            else:
                st.sidebar.caption(f"**{n}** words in deck")
        if not filtered:
            st.sidebar.warning(
                explain_empty_comfort_filter(
                    all_words=all_words,
                    section_filtered=section_filtered,
                    comfort_filter=comfort_filter,
                    section=section,
                    images_only=images_only,
                    cefr_level=_cefr(),
                )
            )
            fix_col1, fix_col2 = st.sidebar.columns(2)
            with fix_col1:
                if comfort_filter != "all" and st.button("All words", key=f"comfort_reset_{_cefr()}"):
                    st.session_state[practice_key] = "all"
                    st.session_state.deck_filter_key = None
                    st.session_state.pop("deck", None)
                    st.rerun()
            with fix_col2:
                if section != "All sections" and st.button("All sections", key=f"section_reset_{_cefr()}"):
                    st.session_state[_section_key()] = "All sections"
                    st.session_state.deck_filter_key = None
                    st.session_state.pop("deck", None)
                    st.rerun()
            if images_only and st.sidebar.button(
                "Include words without pictures",
                key=f"images_reset_{_cefr()}",
            ):
                st.session_state[_images_only_key()] = False
                st.session_state.deck_filter_key = None
                st.session_state.pop("deck", None)
                st.rerun()
        elif not section_filtered and images_only:
            st.sidebar.info("Turn off **Only words with pictures** to see verbs and grammar words.")
    elif mode == "Browse list":
        st.sidebar.caption(f"{len(all_words)} words · browse shows full list")
    else:
        st.sidebar.caption(f"{len(all_words)} words")

    if mode == "Flashcards":
        st.sidebar.divider()
        front_mode = st.sidebar.radio(
            "Front of card",
            FRONT_MODES,
            index=FRONT_MODES.index(st.session_state.get("front_mode", "German")),
            help="Choose what you see first. Flip to reveal the other side.",
        )
        if st.session_state.get("front_mode") != front_mode:
            st.session_state.front_mode = front_mode
            st.session_state.flipped = False
        else:
            st.session_state.front_mode = front_mode

        font_label = st.sidebar.select_slider(
            "Card font size",
            options=list(FONT_SIZE_OPTIONS.keys()),
            value=st.session_state.get("font_size", "Normal"),
        )
        st.session_state.font_size = font_label

        st.sidebar.divider()
        stats = comfort_stats(filtered, _cefr())
        st.sidebar.caption("**Your comfort** (this deck)")
        st.sidebar.caption(
            f"😊 Comfortable: **{stats.comfortable}** · "
            f"📖 Learning: **{stats.learning}** · "
            f"💪 Need practice: **{stats.need_practice}**"
        )
        if stats.rated:
            st.sidebar.caption(f"Rated {stats.rated}/{stats.total} words")

    if mode == "Flashcards" and st.sidebar.button("Shuffle deck"):
        st.session_state.deck = (
            weighted_shuffle_deck(filtered, _cefr())
            if st.session_state.get("comfort_weighted", True)
            else shuffle_deck(filtered)
        )
        st.session_state.deck_filter_key = _deck_filter_key(
            filtered,
            cefr_level=_cefr(),
            vocab_rev=vocabulary_revision(_cefr()),
        )
        st.session_state.card_i = 0
        st.session_state.flipped = False
        st.session_state.card_history = []

    if mode == "Flashcards" and st.sidebar.button("Reset order"):
        st.session_state.deck = list(filtered)
        st.session_state.deck_filter_key = _deck_filter_key(
            filtered,
            cefr_level=_cefr(),
            vocab_rev=vocabulary_revision(_cefr()),
        )
        st.session_state.card_i = 0
        st.session_state.flipped = False
        st.session_state.card_history = []

    return filtered, meta


def render_flashcard_image(word: Word) -> None:
    """Show a picture above the card when one is available (no placeholder card)."""
    if not word.has_image:
        return

    cached = image_path(word.id)
    if cached.exists() and cached.stat().st_size > 500:
        st.image(str(cached), use_container_width=True)
        return

    from a1.images import image_queries_for

    if not image_queries_for(word.german, word.english, word.section) and not word.image_query:
        return

    with st.spinner("Loading image…"):
        path = ensure_image(
            word.id,
            word.german,
            word.english,
            word.image_query,
            section=word.section,
        )
    if path and path.exists():
        st.image(str(path), use_container_width=True)


def render_word_image(word: Word, *, width: int | None = None, lazy: bool = False) -> None:
    from a1.images import image_queries_for

    if not word.has_image:
        st.markdown(placeholder_svg(word.german, word.english), unsafe_allow_html=True)
        return

    cached = image_path(word.id)
    if cached.exists() and cached.stat().st_size > 500:
        if width:
            st.image(str(cached), width=width)
        else:
            st.image(str(cached), use_container_width=True)
        return

    if not image_queries_for(word.german, word.english, word.section) and not word.image_query:
        st.markdown(placeholder_svg(word.german, word.english), unsafe_allow_html=True)
        return

    if lazy:
        if st.button("Load image from web", key=f"load_img_{word.id}", use_container_width=True):
            with st.spinner("Loading image…"):
                path = ensure_image(
                    word.id,
                    word.german,
                    word.english,
                    word.image_query,
                    section=word.section,
                )
            if path:
                st.rerun()
            else:
                st.info("No image found online for this word.")
        return

    with st.spinner("Loading image…"):
        path = ensure_image(
            word.id,
            word.german,
            word.english,
            word.image_query,
            section=word.section,
        )
    if path and path.exists():
        if width:
            st.image(str(path), width=width)
        else:
            st.image(str(path), use_container_width=True)
    else:
        st.info("No image found online for this word.")
        st.markdown(placeholder_svg(word.german, word.english), unsafe_allow_html=True)


def _german_html(word: Word) -> str:
    de = html.escape(word.german)
    if word.article:
        art = html.escape(word.article)
        return f"<p class='flash-de'><span class='flash-article'>{art}</span>&nbsp;{de}</p>"
    return f"<p class='flash-de'>{de}</p>"


def _card_face(word: Word, front_mode: str, flipped: bool) -> tuple[str, str, str, str | None]:
    """Return label, main HTML, sub HTML, and optional caption for the card face."""
    en = english_short(word.english)
    pron = html.escape(pronunciation_display(word))

    if front_mode == "German":
        if not flipped:
            return (
                "German",
                _german_html(word),
                f"<p class='flash-pron'>{pron}</p>",
                None,
            )
        return (
            "English",
            f"<p class='flash-en'>{html.escape(en)}</p>",
            f"<p class='flash-pron'>{html.escape(word.sentence_de)}</p>",
            word.sentence_en,
        )

    if front_mode == "English":
        if not flipped:
            return (
                "English",
                f"<p class='flash-en'>{html.escape(en)}</p>",
                "<p class='flash-pron'>&nbsp;</p>",
                None,
            )
        return (
            "German",
            _german_html(word),
            f"<p class='flash-pron'>{pron}</p>",
            word.sentence_de,
        )

    # German + English on front; flip shows example sentences.
    if not flipped:
        return (
            "German + English",
            _german_html(word),
            f"<p class='flash-en'>{html.escape(en)}</p><p class='flash-pron'>{pron}</p>",
            None,
        )
    return (
        "Example",
        f"<p class='flash-pron'>{html.escape(word.sentence_de)}</p>",
        "",
        word.sentence_en,
    )


def render_flashcard_face(word: Word, *, flipped: bool) -> None:
    front_mode = st.session_state.get("front_mode", "German")
    label, main_html, sub_html, caption = _card_face(word, front_mode, flipped)

    with st.container(border=True):
        st.markdown('<div class="flash-card-marker"></div>', unsafe_allow_html=True)
        st.markdown(f'<p class="flash-card-label">{label}</p>', unsafe_allow_html=True)

        caption_html = html.escape(caption) if caption else "&#8203;"
        st.markdown(
            f"""<div class="flash-card">
  <div class="flash-card-body">
    {main_html}
    {sub_html}
  </div>
  <div class="flash-card-caption">{caption_html}</div>
</div>""",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="flash-card-nav-marker"></div>', unsafe_allow_html=True)
        nav_prev, nav_flip, nav_next = st.columns([1, 1, 1])
        with nav_prev:
            if st.button("◀ Prev", key="card_prev", help="Previous card", use_container_width=True):
                _go_prev_card()
                st.rerun()
        with nav_flip:
            if st.button("↻ Flip", key="flip_card", help="Flip card", use_container_width=True):
                st.session_state.flipped = not flipped
                st.rerun()
        with nav_next:
            if st.button("Next ▶", key="card_next", help="Next card", use_container_width=True):
                _go_next_card()
                st.rerun()


def render_comfort_controls(word: Word) -> None:
    """Rate how well you know this word — saved locally, affects how often it appears."""
    saved = get_comfort_level(word.id, _cefr())
    label = COMFORT_LABELS.get(saved, "Not rated yet") if saved else "Not rated yet"
    stars = "★" * effective_level(word.id, _cefr()) + "☆" * (5 - effective_level(word.id, _cefr()))
    st.caption(f"**Comfort:** {label} · {stars}")

    c1, c2, c3, c4, c5 = st.columns(5)
    buttons = (
        (c1, 1, "😓 1"),
        (c2, 2, "2"),
        (c3, 3, "3 OK"),
        (c4, 4, "4"),
        (c5, 5, "😊 5"),
    )
    for col, level, text in buttons:
        with col:
            btn_type = "primary" if saved == level else "secondary"
            if st.button(text, key=f"comfort_{word.id}_{level}", type=btn_type, use_container_width=True):
                set_comfort_level(word.id, level, _cefr())
                st.rerun()


def render_flashcards(word: Word) -> None:
    handle_load_image_query()
    st.markdown('<div class="flashcard-layout">', unsafe_allow_html=True)

    flipped = st.session_state.flipped
    st.progress((st.session_state.card_i + 1) / max(len(st.session_state.deck), 1))
    st.caption(f"Card {st.session_state.card_i + 1} / {len(st.session_state.deck)} · {word.section}")

    render_flashcard_image(word)
    render_flashcard_face(word, flipped=flipped)
    render_comfort_controls(word)

    if st.button("Random card", use_container_width=True):
        _go_random_card()
        st.rerun()

    st.divider()
    st.subheader("Listen")
    de_path = get_word_audio_path(word.id, "de")
    en_path = get_word_audio_path(word.id, "en")
    if de_path or en_path:
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            if de_path:
                st.caption("🔊 German word")
                st.audio(str(de_path))
            else:
                render_word_audio(
                    "🔊 German word",
                    word.id,
                    "de",
                    german_de_speech(word),
                    lang="de-DE",
                    button_id=f"speak_de_{word.id}",
                    rate=0.78,
                )
        with ac2:
            if en_path:
                st.caption("🔊 English meaning")
                st.audio(str(en_path))
            else:
                render_word_audio(
                    "🔊 English meaning",
                    word.id,
                    "en",
                    english_short(word.english),
                    lang="en-US",
                    button_id=f"speak_en_{word.id}",
                    rate=1.0,
                )
        with ac3:
            if st.button("🖼 Load image", key=f"load_img_listen_{word.id}", use_container_width=True):
                ensure_image(
                    word.id,
                    word.german,
                    word.english,
                    word.image_query,
                    section=word.section,
                )
                st.rerun()
    else:
        render_listen_toolbar(
            word_id=word.id,
            german_text=german_de_speech(word),
            english_text=english_short(word.english),
        )

    if is_custom_word(word.id, _cefr()):
        st.divider()
        render_custom_card_actions(word, key_prefix="flash")

    st.markdown("</div>", unsafe_allow_html=True)


def render_listen() -> None:
    st.header("Full audio courses")
    st.caption(f"Files in {FULL_AUDIO_DIR}")

    sync_result = st.session_state.pop("_mp3_sync_result", None)
    if sync_result:
        if sync_result.get("message"):
            if sync_result.get("success"):
                st.success(sync_result["message"])
            else:
                st.info(sync_result["message"])
        for err in sync_result.get("errors", []):
            st.warning(err)

    missing_all = courses_missing()
    clip_count = clip_words_available("de_en")

    if missing_all and clip_count == 0:
        st.info(
            "Course MP3 files are not on disk yet. Generate them once (needs **internet**). "
            "This creates three long audio files with **der/die/das** articles on nouns."
        )
        if st.button("Generate full course MP3s", type="primary", use_container_width=True):
            import subprocess
            import sys

            with st.status("Building audio courses… this can take 15–30 minutes.", expanded=True) as status:
                st.write("Using Microsoft edge-tts. Do not close the app.")
                try:
                    proc = subprocess.run(
                        [sys.executable, "scripts/build_german_vocab_learn_pack.py", "--audio-only"],
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=7200,
                    )
                    if proc.returncode == 0:
                        status.update(label="Done!", state="complete")
                        invalidate_extended_courses()
                        st.rerun()
                    else:
                        status.update(label="Build failed", state="error")
                        tail = (proc.stderr or proc.stdout or "")[-2000:]
                        st.code(tail or "Unknown error")
                except subprocess.TimeoutExpired:
                    status.update(label="Timed out", state="error")
                    st.error("Build took too long. Run from terminal instead (see below).")
                except Exception as exc:
                    status.update(label="Build failed", state="error")
                    st.error(str(exc))

        st.code(
            "cd /Users/tapasya/Work/OFM/Code/A1\n"
            ".venv/bin/python scripts/build_german_vocab_learn_pack.py --audio-only",
            language="bash",
        )
        st.caption("Or generate per-word clips first, then merge:")
        st.code(
            ".venv/bin/python scripts/pregenerate_word_audio.py",
            language="bash",
        )

    elif missing_all and clip_count > 0:
        st.info(f"Found **{clip_count}** words with saved clips. Build courses from those clips.")
        if not ffmpeg_available():
            st.warning("Install **ffmpeg** to merge clips: `brew install ffmpeg`")
        elif st.button("Build courses from word clips", type="primary", use_container_width=True):
            invalidate_extended_courses()
            st.rerun()

    total_custom, in_both, in_de_only, skipped = extended_course_status()
    if total_custom:
        if in_de_only == 0:
            st.warning(
                f"You have **{total_custom}** custom card{'s' if total_custom != 1 else ''}, "
                "but none are in the course MP3s yet. "
                "Use the button below — uses **Katja/Jenny** when online, **Mac voice** offline, "
                "or your saved recordings."
            )
        elif in_both < total_custom:
            st.info(
                f"**{in_both}** of **{total_custom}** custom cards are in the German↔English courses; "
                f"**{in_de_only}** in German-only (need both German and English clips for bilingual courses)."
            )
        else:
            st.success(
                f"All **{total_custom}** custom cards have pronunciation clips "
                f"({in_both} in German↔English courses, {in_de_only} in German-only)."
            )
        if skipped:
            with st.expander("Custom cards missing from MP3"):
                for line in skipped:
                    st.markdown(f"- {line}")

        need_sync = in_de_only < total_custom or not any(
            course_audio_path(m)[2] == "plus_custom" for m in ("de_en", "en_de", "de_only")
        )
        if need_sync:
            btn_label = (
                "Generate pronunciation & add custom cards to MP3s"
                if in_de_only < total_custom
                else "Rebuild course MP3s with custom cards"
            )
            if not ffmpeg_available():
                st.caption(
                    "Install **ffmpeg** to merge: `brew install ffmpeg` "
                    "or `.venv/bin/pip install imageio-ffmpeg`"
                )
            elif st.button(btn_label, type="primary", use_container_width=True, key="rebuild_plus_custom"):
                try:
                    with st.status("Generating clips and building MP3s…", expanded=True) as status:

                        def _progress(msg: str) -> None:
                            status.update(label=msg)
                            st.write(msg)

                        ok_modes, sync_errors, new_both, new_de = rebuild_plus_custom_courses(
                            progress=_progress
                        )
                    if ok_modes:
                        from a1.full_course import MODE_LABELS

                        names = ", ".join(MODE_LABELS[m] for m in ok_modes)
                        msg = (
                            f"Updated {names}. "
                            f"{new_both} card{'s' if new_both != 1 else ''} in bilingual courses, "
                            f"{new_de} in German-only."
                        )
                        if sync_errors:
                            msg += f" ({len(sync_errors)} card{'s' if len(sync_errors) != 1 else ''} skipped — see below.)"
                        st.session_state["_mp3_sync_result"] = {
                            "success": True,
                            "message": msg,
                            "errors": sync_errors,
                        }
                    else:
                        st.session_state["_mp3_sync_result"] = {
                            "success": False,
                            "message": "Could not build course MP3s.",
                            "errors": sync_errors or ["Unknown error — see terminal for details."],
                        }
                except Exception as exc:
                    st.session_state["_mp3_sync_result"] = {
                        "success": False,
                        "message": "Build failed.",
                        "errors": [str(exc)],
                    }
                st.rerun()

    courses = [
        ("German → English", "de_en"),
        ("English → German", "en_de"),
        ("German only", "de_only"),
    ]
    for label, mode in courses:
        p, has_custom, source = course_audio_path(mode)
        if p:
            st.subheader(label)
            if source == "plus_custom":
                st.caption("Includes your custom cards at the end (Katja/Jenny voice, same pauses as the course).")
            elif source == "clips":
                n = clip_words_available(mode if mode != "de_only" else "de_only")
                st.caption(f"Built from {n} saved word clips.")
            elif has_custom:
                st.caption("Includes your custom cards at the end.")
            st.audio(str(p))
        else:
            st.warning(f"Missing course audio for {label}.")


def render_browse(words: list[Word]) -> None:
    st.header("Word list")
    if not words:
        st.warning("No words loaded for this level.")
        return
    st.caption("Full list for the selected CEFR level (sidebar section filter does not apply here).")
    query = st.text_input(
        "Search",
        placeholder="German, English, or sentence…",
        key="browse_search",
    )
    shown = search_words(words, query)
    custom_n = sum(1 for w in shown if is_custom_word(w.id, _cefr()))
    st.caption(
        f"{len(shown)} word{'s' if len(shown) != 1 else ''}"
        + (f" ({custom_n} custom)" if custom_n else "")
    )

    if not shown:
        st.info("No words match your search.")
        return

    if query.strip():
        display = shown
    else:
        custom_cards = [w for w in shown if is_custom_word(w.id, _cefr())]
        rest = [w for w in shown if not is_custom_word(w.id, _cefr())]
        display = custom_cards + rest

    if custom_cards := [w for w in display if is_custom_word(w.id, _cefr())]:
        st.subheader(f"My cards ({len(custom_cards)})")
        for w in custom_cards:
            _render_browse_row(w)
        if rest := [w for w in display if not is_custom_word(w.id, _cefr())]:
            st.divider()
            st.subheader(f"Course vocabulary ({len(rest)})")
            for w in rest:
                _render_browse_row(w)
    else:
        for w in display:
            _render_browse_row(w)


def _browse_title(w: Word) -> str:
    if w.article:
        return f"{w.article} {w.german} — {w.english}"
    return f"{w.german} — {w.english}"


def _render_browse_row(w: Word) -> None:
    with st.expander(_browse_title(w) + (f" · {w.section}" if is_custom_word(w.id, _cefr()) else "")):
        st.write(w.sentence_de)
        st.caption(w.sentence_en)
        audio_de, audio_en = st.columns(2)
        with audio_de:
            render_word_audio(
                "🔊 German",
                w.id,
                "de",
                german_de_speech(w),
                lang="de-DE",
                button_id=f"browse_de_{w.id}",
                rate=0.78,
            )
        with audio_en:
            render_word_audio(
                "🔊 English",
                w.id,
                "en",
                english_short(w.english),
                lang="en-US",
                button_id=f"browse_en_{w.id}",
                rate=1.0,
            )
        render_word_image(w, width=200, lazy=True)
        render_custom_card_actions(w, key_prefix="browse")


def render_add_card(all_words: list[Word]) -> None:
    continue_pending_jobs()

    st.header("Add a new card")
    st.caption("Custom cards are saved locally and appear in Flashcards, Browse, and full MP3 courses.")
    st.caption("Look up and audio use your browser when the app server has no internet.")

    section_options = list(dict.fromkeys([CUSTOM_SECTION, *sections(all_words)]))

    lu_en_col, lu_de_col = st.columns(2)
    with lu_en_col:
        if st.button("Look up English meaning", key="btn_lu_en", use_container_width=True):
            apply_translation(
                st.session_state.get("add_german", ""),
                "de",
                "en",
                "add_english",
                "English meaning",
            )
    with lu_de_col:
        if st.button("Look up German word", key="btn_lu_de", use_container_width=True):
            apply_translation(
                st.session_state.get("add_english", ""),
                "en",
                "de",
                "add_german",
                "German word",
            )

    st.text_input("German word *", placeholder="z.B. Hund", key="add_german")
    st.text_input("English meaning *", placeholder="e.g. dog", key="add_english")

    section = st.selectbox("Section", section_options, index=0, key="add_section")
    new_section = st.text_input(
        "Or new section name",
        placeholder="Leave blank to use selection above",
        key="add_new_section",
    )
    st.selectbox(
        "Article (nouns)",
        ARTICLE_OPTIONS,
        index=0,
        key="add_article",
        help="Auto picks der/die/das when known.",
    )
    pronunciation = st.text_input(
        "Pronunciation (optional)",
        placeholder="Defaults to the German word",
        key="add_pron",
    )
    st.caption("Example sentences — look up fills both fields (with der/die/das on nouns).")
    sent_fill_col, sent_lu_col = st.columns(2)
    with sent_fill_col:
        if st.button("Fill default example", key="btn_fill_sent", use_container_width=True):
            g = st.session_state.get("add_german", "")
            e = st.session_state.get("add_english", "")
            if g.strip() and e.strip():
                art = _article_from_choice(st.session_state.get("add_article", "Auto"))
                de, en = default_example_sentences(g, e, article=art)
                st.session_state.add_sent_de = de
                st.session_state.add_sent_en = en
                st.rerun()
            else:
                st.warning("Enter German and English first.")
    with sent_lu_col:
        if st.button("Look up example sentences", key="btn_lu_sent", use_container_width=True):
            apply_sentences(
                st.session_state.get("add_german", ""),
                st.session_state.get("add_english", ""),
                article=_article_from_choice(st.session_state.get("add_article", "Auto")),
            )

    st.text_area("German example sentence (optional)", key="add_sent_de")
    st.text_area("English example sentence (optional)", key="add_sent_en")

    st.divider()
    st.subheader("Sound")
    st.caption("Record or find pronunciation first, then add the card.")
    audio_col_de, audio_col_en = st.columns(2)
    with audio_col_de:
        render_add_card_audio(
            "German",
            german_with_article(
                st.session_state.get("add_german", ""),
                article=article_for_german(
                    st.session_state.get("add_german", ""),
                    stored=_article_from_choice(st.session_state.get("add_article", "Auto")),
                ),
            ),
            "de-DE",
            state_key="add_de_audio",
            ext_key="add_de_ext",
            rec_key="add_rec_de",
        )
    with audio_col_en:
        render_add_card_audio(
            "English",
            st.session_state.get("add_english", ""),
            "en-US",
            state_key="add_en_audio",
            ext_key="add_en_ext",
            rec_key="add_rec_en",
        )

    has_de = isinstance(st.session_state.get("add_de_audio"), bytes) and st.session_state.get("add_de_audio")
    has_en = isinstance(st.session_state.get("add_en_audio"), bytes) and st.session_state.get("add_en_audio")
    st.checkbox(
        "Add to course MP3s when I press Add card",
        value=True,
        key="add_append_mp3",
        help="Appends with the **same voice and pauses** as the full course MP3s "
        "(German: Katja, English: Jenny). Needs ffmpeg and internet. "
        "Recorded clips are still saved for flashcards.",
    )
    if st.session_state.get("add_append_mp3") and not ffmpeg_available():
        st.caption("Install **ffmpeg** to merge into MP3s: `brew install ffmpeg`")

    if st.button("Add card", type="primary", use_container_width=True):
        german = st.session_state.get("add_german", "")
        english = st.session_state.get("add_english", "")
        if not str(german).strip() or not str(english).strip():
            st.error("German and English are required.")
            return
        try:
            word = add_custom_word(
                german,
                english,
                level_id=_cefr(),
                section=str(st.session_state.get("add_new_section", "")).strip()
                or st.session_state.get("add_section", CUSTOM_SECTION),
                pronunciation=st.session_state.get("add_pron", ""),
                sentence_de=st.session_state.get("add_sent_de", ""),
                sentence_en=st.session_state.get("add_sent_en", ""),
                article=_article_from_choice(st.session_state.get("add_article", "Auto")),
            )
        except ValueError as exc:
            st.error(str(exc))
            return

        for kind, state_key, ext_key in (
            ("de", "add_de_audio", "add_de_ext"),
            ("en", "add_en_audio", "add_en_ext"),
        ):
            data = st.session_state.pop(state_key, None)
            ext = st.session_state.pop(ext_key, None)
            if isinstance(data, bytes) and data:
                save_word_audio(word.id, kind, data, ext or ".webm")

        _refresh_vocabulary()
        msg = f"Added „{word.german}“ → {english_short(word.english)}"

        if st.session_state.get("add_append_mp3"):
            from a1.vocab import get_custom_word

            saved = get_custom_word(word.id) or word
            ok_modes, mp3_errors = append_word_to_courses(saved, generate_missing=True)
            if ok_modes:
                from a1.full_course import MODE_LABELS

                names = ", ".join(MODE_LABELS[m] for m in ok_modes)
                msg += f" Appended to course MP3s: {names}."
            if mp3_errors:
                st.warning("Course MP3: " + " · ".join(mp3_errors))
        else:
            invalidate_extended_courses()

        st.session_state.mode = "Flashcards"
        st.session_state.preferred_section = word.section
        st.session_state.focus_word_id = word.id
        st.success(msg)
        st.rerun()

    custom = load_custom_vocabulary(_cefr())
    if custom:
        st.divider()
        st.subheader(f"Your cards ({len(custom)})")
        st.caption("Open **Manage cards** to edit or delete any of these.")
        for w in reversed(custom[-20:]):
            st.markdown(f"**{w.german}** — {w.english} · _{w.section}_")
            render_custom_card_actions(w, key_prefix="add")


def main() -> None:
    ensure_level_layout()
    _ensure_cefr_session([lv.id for lv in all_levels()])
    if "cefr_level" not in st.session_state:
        st.session_state.cefr_level = default_level_id()
    _sanitize_filter_session()

    all_words = load_app_vocabulary(_cefr())
    filtered, meta = sidebar(all_words)
    mode = st.session_state.get("mode", "Flashcards")

    if mode == "Flashcards" and not filtered:
        practice_key = _comfort_practice_key()
        comfort_filter = normalize_comfort_filter(st.session_state.get(practice_key, "all"))
        section = st.session_state.get(_section_key(), "All sections")
        images_only = bool(st.session_state.get(_images_only_key(), False))
        section_filtered = filter_words(all_words, section, images_only)
        if comfort_filter != "all":
            st.info(
                explain_empty_comfort_filter(
                    all_words=all_words,
                    section_filtered=section_filtered,
                    comfort_filter=comfort_filter,
                    section=section,
                    images_only=images_only,
                    cefr_level=_cefr(),
                )
            )
        else:
            st.warning(
                explain_empty_comfort_filter(
                    all_words=all_words,
                    section_filtered=section_filtered,
                    comfort_filter="all",
                    section=section,
                    images_only=images_only,
                    cefr_level=_cefr(),
                )
            )
        return

    if mode == "Flashcards":
        init_state(filtered, vocab_rev=vocabulary_revision(_cefr()), cefr_level=_cefr())
        if (focus_id := st.session_state.pop("focus_word_id", None)) is not None:
            for i, w in enumerate(st.session_state.deck):
                if w.id == focus_id:
                    st.session_state.card_i = i
                    st.session_state.flipped = False
                    break

    if mode == "Flashcards":
        scale = FONT_SIZE_OPTIONS.get(st.session_state.get("font_size", "Normal"), 1.0)
        inject_card_font_css(scale)
        word = current_card()
        if word:
            render_flashcards(word)
        else:
            st.warning("No card loaded. Click **Shuffle deck** in the sidebar.")
    elif mode == "Listen — full courses":
        st.title(f"🇩🇪 {meta.title}")
        render_listen()
    elif mode == "Add card":
        st.title(f"🇩🇪 {meta.title}")
        render_add_card(all_words)
    elif mode == "Manage cards":
        st.title(f"🇩🇪 {meta.title}")
        render_manage_cards(all_words)
    else:
        st.title(f"🇩🇪 {meta.title}")
        render_browse(all_words)


if __name__ == "__main__":
    main()
