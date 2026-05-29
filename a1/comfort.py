"""Per-word comfort levels — less comfortable words appear more often."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone

from a1.levels import comfort_path, normalize_level_id
from a1.vocab import Word

MIN_LEVEL = 1
MAX_LEVEL = 5
DEFAULT_LEVEL = 3

COMFORT_LABELS = {
    1: "Still learning",
    2: "Shaky",
    3: "OK",
    4: "Good",
    5: "Comfortable",
}

# Sidebar “Practice by comfort” options (key → label)
COMFORT_FILTERS: tuple[tuple[str, str], ...] = (
    ("all", "All words"),
    ("unrated", "Not rated yet"),
    ("weak", "Need practice (1–2 or unrated)"),
    ("1", "1 — Still learning"),
    ("2", "2 — Shaky"),
    ("3", "3 — OK"),
    ("4", "4 — Good"),
    ("5", "5 — Comfortable"),
)


def comfort_filter_label(filter_key: str) -> str:
    for key, label in COMFORT_FILTERS:
        if key == filter_key:
            return label
    return filter_key


def normalize_comfort_filter(filter_key: str | int | bool | None) -> str:
    """Map session/widget values to a valid comfort filter key."""
    valid = {k for k, _ in COMFORT_FILTERS}
    if filter_key is None:
        return "all"
    if isinstance(filter_key, bool):
        return "all"
    text = str(filter_key).strip()
    # Drop dynamic counts from sidebar labels, e.g. "All words (460)".
    if "(" in text:
        text = text.split("(", 1)[0].strip()
    if text in valid:
        return text
    lower = text.lower()
    for key, label in COMFORT_FILTERS:
        if lower == label.lower():
            return key
    return "all"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_raw(level_id: str | None = None) -> dict:
    path = comfort_path(normalize_level_id(level_id))
    if not path.exists():
        return {"version": 1, "words": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "words": {}}
    if not isinstance(data, dict):
        return {"version": 1, "words": {}}
    data.setdefault("words", {})
    return data


def _save_raw(data: dict, level_id: str | None = None) -> None:
    path = comfort_path(normalize_level_id(level_id))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_level(word_id: int, cefr_level: str | None = None) -> int | None:
    entry = _load_raw(cefr_level)["words"].get(str(word_id))
    if not entry:
        return None
    level = int(entry.get("level", DEFAULT_LEVEL))
    return max(MIN_LEVEL, min(MAX_LEVEL, level))


def effective_level(word_id: int, cefr_level: str | None = None) -> int:
    level = get_level(word_id, cefr_level)
    if level is None:
        return MIN_LEVEL
    return level


def set_level(word_id: int, level: int, cefr_level: str | None = None) -> int:
    level = max(MIN_LEVEL, min(MAX_LEVEL, int(level)))
    cefr_level = normalize_level_id(cefr_level)
    data = _load_raw(cefr_level)
    words = data["words"]
    key = str(word_id)
    prev = words.get(key, {})
    words[key] = {
        "level": level,
        "seen": int(prev.get("seen", 0)) + 1,
        "updated": _now_iso(),
    }
    _save_raw(data, cefr_level)
    return level


def weight_for_level(level: int) -> int:
    level = max(MIN_LEVEL, min(MAX_LEVEL, level))
    return MAX_LEVEL + MIN_LEVEL - level


def weight_for_word(word_id: int, cefr_level: str | None = None) -> int:
    return weight_for_level(effective_level(word_id, cefr_level))


def weighted_pick(
    deck: list[Word],
    *,
    exclude_id: int | None = None,
    cefr_level: str | None = None,
) -> Word | None:
    if not deck:
        return None
    pool = [w for w in deck if exclude_id is None or w.id != exclude_id]
    if not pool:
        pool = list(deck)
    weights = [weight_for_word(w.id, cefr_level) for w in pool]
    return random.choices(pool, weights=weights, k=1)[0]


def index_of_word(deck: list[Word], word_id: int) -> int:
    for i, w in enumerate(deck):
        if w.id == word_id:
            return i
    return 0


@dataclass
class ComfortStats:
    total: int
    rated: int
    comfortable: int
    learning: int
    need_practice: int
    avg_level: float | None


def comfort_stats(words: list[Word], cefr_level: str | None = None) -> ComfortStats:
    if not words:
        return ComfortStats(0, 0, 0, 0, 0, None)
    comfortable = learning = need_practice = rated = 0
    levels: list[int] = []
    for w in words:
        level = get_level(w.id, cefr_level)
        if level is None:
            need_practice += 1
            levels.append(MIN_LEVEL)
            continue
        rated += 1
        levels.append(level)
        if level >= 4:
            comfortable += 1
        elif level >= 2:
            learning += 1
        else:
            need_practice += 1
    avg = sum(levels) / len(levels) if levels else None
    return ComfortStats(
        total=len(words),
        rated=rated,
        comfortable=comfortable,
        learning=learning,
        need_practice=need_practice,
        avg_level=avg,
    )


def weighted_shuffle_deck(words: list[Word], cefr_level: str | None = None) -> list[Word]:
    if len(words) <= 1:
        return list(words)
    remaining = list(words)
    ordered: list[Word] = []
    while remaining:
        weights = [weight_for_word(w.id, cefr_level) for w in remaining]
        pick = random.choices(remaining, weights=weights, k=1)[0]
        ordered.append(pick)
        remaining.remove(pick)
    return ordered


def filter_words_by_comfort(
    words: list[Word],
    filter_key: str | int | bool | None,
    cefr_level: str | None = None,
) -> list[Word]:
    """Keep only words matching the chosen comfort filter."""
    key = normalize_comfort_filter(filter_key)
    if key == "all":
        return list(words)
    out: list[Word] = []
    for w in words:
        level = get_level(w.id, cefr_level)
        if key == "unrated":
            if level is None:
                out.append(w)
        elif key == "weak":
            if level is None or level <= 2:
                out.append(w)
        elif key in {"1", "2", "3", "4", "5"}:
            if level == int(key):
                out.append(w)
    return out


def comfort_revision(cefr_level: str | None = None) -> float:
    """Changes when any comfort rating is saved — use to invalidate cached decks."""
    path = comfort_path(normalize_level_id(cefr_level))
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def count_by_comfort_filter(
    words: list[Word],
    filter_key: str | int | bool | None,
    cefr_level: str | None = None,
) -> int:
    return len(filter_words_by_comfort(words, filter_key, cefr_level))


def explain_empty_comfort_filter(
    *,
    all_words: list[Word],
    section_filtered: list[Word],
    comfort_filter: str,
    section: str,
    images_only: bool,
    cefr_level: str | None = None,
) -> str:
    """Actionable hint when section/images/comfort filters leave no flashcards."""
    key = normalize_comfort_filter(comfort_filter)
    if key == "all":
        if images_only and section_filtered:
            return (
                "No words in this section have pictures. Uncheck **Only words with pictures** "
                "or choose another section."
            )
        if not section_filtered:
            return f"No words in section **{section}**. Choose **All sections** or another section."
        return "No words match your filters."

    in_section = count_by_comfort_filter(section_filtered, key, cefr_level)
    in_level = count_by_comfort_filter(all_words, key, cefr_level)

    if images_only and not section_filtered:
        if section != "All sections":
            return (
                f"No words with pictures in **{section}**. Uncheck **Only words with pictures**, "
                "or choose a section like Food, Home, or Family."
            )
        return "No words with pictures in this level. Uncheck **Only words with pictures**."

    if in_section == 0 and in_level > 0 and section != "All sections":
        return (
            f"You have **{in_level}** word(s) at this comfort level in other sections. "
            f"Set **Section** to **All sections**, or rate cards in **{section}**."
        )

    if key in {"1", "2", "3", "4", "5"} and in_level == 0:
        return (
            f"No cards rated **{comfort_filter_label(key)}** yet. "
            "Set **Practice by comfort** to **All words**, flip cards, and tap **1–5** below each card."
        )

    if key == "unrated" and in_level == 0:
        return "Every word in this level is already rated. Pick a comfort level (1–5) instead."

    if key == "weak" and in_level == 0:
        return "No words need practice at this level (all rated 3–5). Try **All words** or a specific level."

    return (
        "No words match this comfort filter in the current section. "
        "Try **All sections** or **All words**, then rate cards with 1–5."
    )
