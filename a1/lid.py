"""Leben in Deutschland test questions and study progress."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from a1.config import DATA_DIR

LID_DIR = DATA_DIR / "lid"
QUESTIONS_JSON = LID_DIR / "questions.json"
PROGRESS_JSON = LID_DIR / "progress.json"

LID_FILTERS: tuple[tuple[str, str], ...] = (
    ("all", "All questions"),
    ("unrated", "Not rated yet"),
    ("weak", "Need practice (1–2 or unrated)"),
    ("learning", "Still learning (3)"),
    ("learned", "Learned (4–5)"),
    ("1", "1 — Still learning"),
    ("2", "2 — Shaky"),
    ("3", "3 — OK"),
    ("4", "4 — Good"),
    ("5", "5 — Comfortable"),
)


@dataclass(frozen=True)
class LiDQuestion:
    id: str
    part: str
    state: str | None
    num: int
    question_de: str
    question_en: str
    options_de: tuple[str, ...]
    options_en: tuple[str, ...]
    correct: str | None
    has_images: bool
    category: str

    @classmethod
    def from_dict(cls, d: dict) -> LiDQuestion:
        opts_de = d.get("options_de") or []
        opts_en = d.get("options_en") or list(opts_de)
        while len(opts_en) < len(opts_de):
            opts_en.append(opts_de[len(opts_en)])
        correct = d.get("correct")
        if correct:
            correct = str(correct).lower()
        return cls(
            id=str(d["id"]),
            part=str(d.get("part", "general")),
            state=d.get("state"),
            num=int(d.get("num", 0)),
            question_de=str(d.get("question_de", "")),
            question_en=str(d.get("question_en", "")),
            options_de=tuple(str(x) for x in opts_de),
            options_en=tuple(str(x) for x in opts_en[: len(opts_de)]),
            correct=correct if correct in ("a", "b", "c", "d") else None,
            has_images=bool(d.get("has_images")),
            category=str(d.get("category", "")),
        )


def lid_filter_label(key: str) -> str:
    for k, label in LID_FILTERS:
        if k == key:
            return label
    return key


def normalize_lid_filter(value: str | None) -> str:
    valid = {k for k, _ in LID_FILTERS}
    if value in valid:
        return str(value)
    return "all"


def load_questions() -> list[LiDQuestion]:
    if not QUESTIONS_JSON.exists():
        return []
    data = json.loads(QUESTIONS_JSON.read_text(encoding="utf-8"))
    return [LiDQuestion.from_dict(q) for q in data.get("questions", [])]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_progress() -> dict:
    if not PROGRESS_JSON.exists():
        return {"version": 1, "questions": {}}
    try:
        data = json.loads(PROGRESS_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "questions": {}}
    data.setdefault("questions", {})
    return data


def _save_progress(data: dict) -> None:
    LID_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_level(question_id: str) -> int | None:
    entry = _load_progress()["questions"].get(question_id)
    if not entry:
        return None
    return max(1, min(5, int(entry.get("level", 1))))


def set_level(question_id: str, level: int) -> int:
    level = max(1, min(5, int(level)))
    data = _load_progress()
    prev = data["questions"].get(question_id, {})
    data["questions"][question_id] = {
        "level": level,
        "seen": int(prev.get("seen", 0)) + 1,
        "updated": _now_iso(),
    }
    _save_progress(data)
    return level


def filter_questions(
    questions: list[LiDQuestion],
    *,
    part: str = "all",
    state: str | None = None,
    comfort_filter: str = "all",
) -> list[LiDQuestion]:
    out = list(questions)
    if part == "general":
        out = [q for q in out if q.part == "general"]
    elif part == "state":
        out = [q for q in out if q.part == "state"]
        if state and state != "All states":
            out = [q for q in out if q.state == state]

    key = normalize_lid_filter(comfort_filter)
    if key == "all":
        return out
    filtered: list[LiDQuestion] = []
    for q in out:
        level = get_level(q.id)
        if key == "unrated":
            if level is None:
                filtered.append(q)
        elif key == "weak":
            if level is None or level <= 2:
                filtered.append(q)
        elif key == "learning":
            if level == 3:
                filtered.append(q)
        elif key == "learned":
            if level is not None and level >= 4:
                filtered.append(q)
        elif key in {"1", "2", "3", "4", "5"}:
            if level == int(key):
                filtered.append(q)
    return filtered


def states_in_catalog(questions: list[LiDQuestion]) -> list[str]:
    return sorted({q.state for q in questions if q.state})
