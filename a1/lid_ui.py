"""Streamlit UI for Leben in Deutschland practice test."""

from __future__ import annotations

import random

import streamlit as st

from a1.comfort import COMFORT_LABELS, stars_display
from a1.lid import (
    LID_FILTERS,
    LiDQuestion,
    filter_questions,
    get_level,
    lid_filter_label,
    load_questions,
    normalize_lid_filter,
    set_level,
    states_in_catalog,
)


def _init_lid_session(questions: list[LiDQuestion]) -> None:
    if "lid_pool" not in st.session_state or st.session_state.get("lid_pool_key") != _pool_key():
        st.session_state.lid_pool = list(questions)
        st.session_state.lid_index = 0
        st.session_state.lid_pool_key = _pool_key()
    if "lid_lang" not in st.session_state:
        st.session_state.lid_lang = "de"
    if "lid_answered" not in st.session_state:
        st.session_state.lid_answered = {}


def _pool_key() -> tuple:
    return (
        st.session_state.get("lid_part", "all"),
        st.session_state.get("lid_state", "All states"),
        normalize_lid_filter(st.session_state.get("lid_comfort_filter", "all")),
    )


def _current_question() -> LiDQuestion | None:
    pool: list[LiDQuestion] = st.session_state.get("lid_pool") or []
    if not pool:
        return None
    return pool[st.session_state.lid_index % len(pool)]


def _option_labels(q: LiDQuestion) -> list[str]:
    lang = st.session_state.get("lid_lang", "de")
    opts = q.options_de if lang == "de" else q.options_en
    letters = ["A", "B", "C", "D"]
    return [f"{letters[i]}. {opts[i]}" for i in range(min(4, len(opts)))]


def render_lid_test_sidebar(questions: list[LiDQuestion]) -> list[LiDQuestion]:
    st.sidebar.subheader("Leben in Deutschland")
    if not questions:
        st.sidebar.warning("No questions loaded. Run: `python scripts/import_lid_pdf.py`")
        return []

    matched = sum(1 for q in questions if q.correct in ("a", "b", "c", "d"))
    st.sidebar.caption(f"{len(questions)} questions · {matched} with verified answers")

    part = st.sidebar.radio(
        "Question set",
        ["all", "general", "state"],
        format_func=lambda x: {"all": "All", "general": "Bundesweit (300)", "state": "By Bundesland"}.get(x, x),
        key="lid_part",
    )
    state = "All states"
    if part in ("all", "state"):
        states = ["All states"] + states_in_catalog(questions)
        state = st.sidebar.selectbox("Bundesland", states, key="lid_state")

    filter_keys = [k for k, _ in LID_FILTERS]
    st.sidebar.selectbox(
        "Practice by comfort",
        filter_keys,
        format_func=lid_filter_label,
        key="lid_comfort_filter",
    )

    lang = st.sidebar.radio("Language", ["de", "en"], format_func=lambda x: "Deutsch" if x == "de" else "English", key="lid_lang")

    filtered = filter_questions(
        questions,
        part=part,
        state=state,
        comfort_filter=st.session_state.get("lid_comfort_filter", "all"),
    )

    if st.sidebar.button("Shuffle questions", key="lid_shuffle"):
        random.shuffle(filtered)
        st.session_state.lid_pool = filtered
        st.session_state.lid_index = 0
        st.session_state.lid_answered = {}
        st.session_state.lid_pool_key = _pool_key()
        st.rerun()

    if st.sidebar.button("Reset order", key="lid_reset"):
        st.session_state.lid_pool = list(filtered)
        st.session_state.lid_index = 0
        st.session_state.lid_answered = {}
        st.session_state.lid_pool_key = _pool_key()
        st.rerun()

    rated = sum(1 for q in questions if get_level(q.id) is not None)
    st.sidebar.caption(f"Rated {rated}/{len(questions)} questions")
    return filtered


def _render_result_styles() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stRadio"] label[data-checked="true"] div[data-testid="stMarkdownContainer"] p {
            font-weight: 600;
        }
        .lid-correct {
            background: #d4edda !important;
            border: 2px solid #28a745 !important;
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
            margin: 0.25rem 0;
        }
        .lid-wrong {
            background: #f8d7da !important;
            border: 2px solid #dc3545 !important;
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
            margin: 0.25rem 0;
        }
        @media (prefers-color-scheme: dark) {
            .lid-correct { background: #1e3d2a !important; border-color: #4ade80 !important; }
            .lid-wrong { background: #3d1e24 !important; border-color: #f87171 !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_comfort_row(q: LiDQuestion) -> None:
    saved = get_level(q.id)
    label = COMFORT_LABELS.get(saved, "Not rated yet") if saved else "Not rated yet"
    stars = stars_display(saved) if saved else "☆☆☆☆☆"
    st.caption(f"**Comfort:** {label} · {stars}")
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, level, text in ((c1, 1, "😓 1"), (c2, 2, "2"), (c3, 3, "3 OK"), (c4, 4, "4"), (c5, 5, "😊 5")):
        with col:
            btn_type = "primary" if saved == level else "secondary"
            if st.button(text, key=f"lid_comfort_{q.id}_{level}", type=btn_type, use_container_width=True):
                set_level(q.id, level)
                st.rerun()


def render_lid_test() -> None:
    questions = load_questions()
    filtered = render_lid_test_sidebar(questions)
    _render_result_styles()

    st.title("🇩🇪 Leben in Deutschland — Test")
    if not questions:
        st.info(
            "Import the official PDF first:\n\n"
            "`python scripts/import_lid_pdf.py`"
        )
        return

    if not filtered:
        st.warning("No questions match your filters. Try **All** or **Not rated yet**.")
        return

    _init_lid_session(filtered)
    q = _current_question()
    if not q:
        st.warning("No question loaded.")
        return

    pool: list[LiDQuestion] = st.session_state.lid_pool
    st.progress((st.session_state.lid_index + 1) / max(len(pool), 1))
    loc = f"Bundesweit · Aufgabe {q.num}" if q.part == "general" else f"{q.state} · Aufgabe {q.num}"
    st.caption(f"Question {st.session_state.lid_index + 1} / {len(pool)} · {loc}")

    lang = st.session_state.get("lid_lang", "de")
    question_text = q.question_de if lang == "de" else (q.question_en or q.question_de)
    st.subheader(question_text)
    if lang == "de" and q.question_en:
        st.caption(q.question_en)
    elif lang == "en" and q.question_de:
        st.caption(q.question_de)

    if q.has_images:
        st.info("This question refers to images in the official PDF (e.g. Bild 1–4).")

    letters = ["a", "b", "c", "d"]
    labels = _option_labels(q)
    answer_key = f"lid_pick_{q.id}_{st.session_state.lid_index}"

    if not q.correct:
        st.warning("Correct answer not verified for this question — practice only.")

    submitted = st.session_state.lid_answered.get(q.id)
    choice = st.radio(
        "Choose an answer",
        options=labels[: len(q.options_de)],
        key=answer_key,
        disabled=submitted is not None,
    )

    col_check, col_next, col_prev = st.columns(3)
    with col_check:
        if st.button("Check answer", key=f"lid_check_{q.id}", disabled=submitted is not None or not q.correct):
            pick_idx = labels.index(choice) if choice in labels else -1
            if pick_idx >= 0:
                st.session_state.lid_answered[q.id] = letters[pick_idx]
                st.rerun()
    with col_next:
        if st.button("Next ▶", key="lid_next"):
            st.session_state.lid_index = (st.session_state.lid_index + 1) % len(pool)
            st.rerun()
    with col_prev:
        if st.button("◀ Prev", key="lid_prev"):
            st.session_state.lid_index = (st.session_state.lid_index - 1) % len(pool)
            st.rerun()

    if submitted and q.correct:
        correct_idx = ord(q.correct) - ord("a")
        st.markdown("**Results:**")
        for i, label in enumerate(labels[: len(q.options_de)]):
            if i == correct_idx:
                st.markdown(f'<div class="lid-correct">{label} ✓</div>', unsafe_allow_html=True)
            elif letters[i] == submitted:
                st.markdown(f'<div class="lid-wrong">{label} ✗</div>', unsafe_allow_html=True)
            else:
                st.caption(label)

        if submitted == q.correct:
            st.success("Correct!")
        else:
            st.error(f"Incorrect. The correct answer is **{labels[correct_idx]}**.")

    st.divider()
    _render_comfort_row(q)
