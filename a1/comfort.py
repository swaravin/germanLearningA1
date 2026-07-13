"""Per-word comfort levels — less comfortable words appear more often."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone

from a1.levels import comfort_path, level_ids, normalize_level_id
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

EXPORT_FORMAT = "german-learn-comfort"
EXPORT_VERSION = 2


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


_RAW_CACHE: dict[str, dict] = {}


def _load_raw(level_id: str | None = None) -> dict:
    key = normalize_level_id(level_id)
    cached = _RAW_CACHE.get(key)
    if cached is not None:
        return cached

    path = comfort_path(key)
    if not path.exists():
        data: dict = {"version": 1, "words": {}}
    else:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {"version": 1, "words": {}}
        if not isinstance(data, dict):
            data = {"version": 1, "words": {}}
        data.setdefault("words", {})
    _RAW_CACHE[key] = data
    return data


def _save_raw(data: dict, level_id: str | None = None) -> None:
    key = normalize_level_id(level_id)
    path = comfort_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _RAW_CACHE[key] = data


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


def _weight_map(words: list[Word], cefr_level: str | None = None) -> dict[int, int]:
    """Comfort weights for a word list — one disk read per level."""
    words_dict = _load_raw(cefr_level)["words"]
    out: dict[int, int] = {}
    for w in words:
        entry = words_dict.get(str(w.id))
        if not entry:
            level = MIN_LEVEL
        else:
            level = max(MIN_LEVEL, min(MAX_LEVEL, int(entry.get("level", DEFAULT_LEVEL))))
        out[w.id] = weight_for_level(level)
    return out


def weighted_shuffle_deck(words: list[Word], cefr_level: str | None = None) -> list[Word]:
    if len(words) <= 1:
        return list(words)
    weights = _weight_map(words, cefr_level)
    # Efraimidis–Spirakis weighted permutation (O(n log n), single comfort load).
    scored = [(random.random() ** (1.0 / weights[w.id]), w) for w in words]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [w for _, w in scored]


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


def stars_display(level: int | None) -> str:
    if level is None:
        return "☆☆☆☆☆"
    lv = max(MIN_LEVEL, min(MAX_LEVEL, int(level)))
    return "★" * lv + "☆" * (5 - lv)


def _sanitize_word_entry(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    try:
        level = int(raw.get("level", DEFAULT_LEVEL))
    except (TypeError, ValueError):
        return None
    level = max(MIN_LEVEL, min(MAX_LEVEL, level))
    seen = int(raw.get("seen", 0) or 0)
    updated = str(raw.get("updated") or _now_iso())
    return {"level": level, "seen": seen, "updated": updated}


def _merge_word_entry(existing: dict | None, incoming: dict) -> dict:
    if not existing:
        return incoming
    ex_updated = str(existing.get("updated", ""))
    in_updated = str(incoming.get("updated", ""))
    return incoming if in_updated >= ex_updated else existing


def export_level_payload(level_id: str | None = None) -> dict:
    level_id = normalize_level_id(level_id)
    data = _load_raw(level_id)
    return {
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "level": level_id,
        "exported_at": _now_iso(),
        "words": data.get("words", {}),
    }


def export_all_payload(levels: list[str] | None = None) -> dict:
    ids = levels or level_ids()
    return {
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "exported_at": _now_iso(),
        "levels": {lid: _load_raw(lid).get("words", {}) for lid in ids},
    }


def _import_words_into_level(
    words: dict,
    level_id: str,
    *,
    merge: bool = True,
) -> int:
    if not isinstance(words, dict):
        return 0
    level_id = normalize_level_id(level_id)
    data = _load_raw(level_id)
    target = data.setdefault("words", {})
    changed = 0
    for word_id, raw in words.items():
        entry = _sanitize_word_entry(raw if isinstance(raw, dict) else {})
        if not entry:
            continue
        key = str(word_id)
        if merge:
            merged = _merge_word_entry(target.get(key), entry)
            if merged != target.get(key):
                target[key] = merged
                changed += 1
        else:
            target[key] = entry
            changed += 1
    if changed:
        _save_raw(data, level_id)
    return changed


def import_comfort_payload(
    payload: dict,
    *,
    default_level: str | None = None,
    merge: bool = True,
) -> tuple[int, list[str]]:
    """Import exported comfort JSON. Returns (words merged, warnings)."""
    warnings: list[str] = []
    if not isinstance(payload, dict):
        return 0, ["Invalid file: expected a JSON object."]

    total = 0
    default_level = normalize_level_id(default_level)

    if isinstance(payload.get("levels"), dict):
        for level_id, words in payload["levels"].items():
            if not isinstance(words, dict):
                warnings.append(f"Skipped level {level_id}: invalid words object.")
                continue
            total += _import_words_into_level(words, str(level_id).lower(), merge=merge)
        return total, warnings

    words = payload.get("words")
    if not isinstance(words, dict):
        return 0, ["Invalid file: missing words or levels."]

    level_id = payload.get("level") or default_level
    if payload.get("format") != EXPORT_FORMAT and "level" not in payload:
        warnings.append(f"Legacy file — imported into **{level_id.upper()}**.")
    total += _import_words_into_level(words, str(level_id).lower(), merge=merge)
    return total, warnings
