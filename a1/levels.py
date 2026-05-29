"""CEFR level registry — add B1/B2/C1/C2 by extending data/levels.json + data/levels/<id>/."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from a1.config import DATA_DIR, ROOT

LEVELS_MANIFEST = DATA_DIR / "levels.json"
LEVELS_ROOT = DATA_DIR / "levels"

# Legacy flat paths (migrated into data/levels/a1/ on first run)
LEGACY_VOCAB = DATA_DIR / "vocabulary.json"
LEGACY_CUSTOM = DATA_DIR / "custom_vocabulary.json"
LEGACY_COMFORT = DATA_DIR / "word_comfort.json"


@dataclass(frozen=True)
class CEFRLevel:
    id: str
    label: str
    title: str
    subtitle: str = ""
    features: tuple[str, ...] = field(default_factory=tuple)

    def has_feature(self, name: str) -> bool:
        return name in self.features


DEFAULT_LEVELS: tuple[CEFRLevel, ...] = (
    CEFRLevel(
        id="a1",
        label="A1",
        title="German A1",
        subtitle="Beginner",
        features=("mp3_courses", "images", "custom_cards", "comfort"),
    ),
    CEFRLevel(
        id="a2",
        label="A2",
        title="German A2",
        subtitle="Elementary",
        features=("images", "custom_cards", "comfort"),
    ),
    CEFRLevel(
        id="c1",
        label="C1",
        title="German C1",
        subtitle="Advanced — Goethe",
        features=("images", "custom_cards", "comfort"),
    ),
)


def level_dir(level_id: str) -> Path:
    return LEVELS_ROOT / level_id


def vocabulary_path(level_id: str) -> Path:
    return level_dir(level_id) / "vocabulary.json"


def custom_vocabulary_path(level_id: str) -> Path:
    return level_dir(level_id) / "custom_vocabulary.json"


def comfort_path(level_id: str) -> Path:
    return level_dir(level_id) / "word_comfort.json"


def _level_from_dict(d: dict) -> CEFRLevel:
    return CEFRLevel(
        id=str(d["id"]).lower(),
        label=str(d.get("label", d["id"]).upper()),
        title=str(d.get("title", f"German {d['id'].upper()}")),
        subtitle=str(d.get("subtitle", "")),
        features=tuple(d.get("features", ("images", "custom_cards", "comfort"))),
    )


def _write_default_manifest() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "default": "a1",
        "levels": [
            {
                "id": lv.id,
                "label": lv.label,
                "title": lv.title,
                "subtitle": lv.subtitle,
                "features": list(lv.features),
            }
            for lv in DEFAULT_LEVELS
        ],
    }
    LEVELS_MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _migrate_legacy_a1() -> None:
    """Move flat data/*.json into data/levels/a1/ once."""
    a1 = level_dir("a1")
    a1.mkdir(parents=True, exist_ok=True)
    pairs = (
        (LEGACY_VOCAB, vocabulary_path("a1")),
        (LEGACY_CUSTOM, custom_vocabulary_path("a1")),
        (LEGACY_COMFORT, comfort_path("a1")),
    )
    for src, dst in pairs:
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)


def ensure_level_layout() -> None:
    if not LEVELS_MANIFEST.exists():
        _write_default_manifest()
    LEVELS_ROOT.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_a1()
    try:
        manifest = json.loads(LEVELS_MANIFEST.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        manifest = {"levels": [{"id": lv.id} for lv in DEFAULT_LEVELS]}
    level_items = manifest.get("levels") if isinstance(manifest.get("levels"), list) else []
    if not level_items:
        level_items = [{"id": lv.id} for lv in DEFAULT_LEVELS]
    for item in level_items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        lid = str(item["id"]).lower()
        level_dir(lid).mkdir(parents=True, exist_ok=True)
        if not vocabulary_path(lid).exists():
            vocabulary_path(lid).write_text(
                json.dumps({"words": []}, indent=2) + "\n",
                encoding="utf-8",
            )
        if not custom_vocabulary_path(lid).exists():
            custom_vocabulary_path(lid).write_text(
                json.dumps({"words": []}, indent=2) + "\n",
                encoding="utf-8",
            )


@lru_cache(maxsize=1)
def _manifest() -> dict:
    if not LEVELS_MANIFEST.exists():
        _write_default_manifest()
    try:
        return json.loads(LEVELS_MANIFEST.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _write_default_manifest()
        return json.loads(LEVELS_MANIFEST.read_text(encoding="utf-8"))


def default_level_id() -> str:
    return str(_manifest().get("default", "a1")).lower()


def all_levels() -> list[CEFRLevel]:
    ensure_level_layout()
    raw = _manifest().get("levels")
    if not isinstance(raw, list) or not raw:
        return list(DEFAULT_LEVELS)
    levels = [_level_from_dict(item) for item in raw if isinstance(item, dict) and item.get("id")]
    return levels or list(DEFAULT_LEVELS)


def level_ids() -> list[str]:
    return [lv.id for lv in all_levels()]


def get_level(level_id: str) -> CEFRLevel:
    key = level_id.lower()
    for lv in all_levels():
        if lv.id == key:
            return lv
    return all_levels()[0]


def normalize_level_id(level_id: str | None) -> str:
    if not level_id:
        return default_level_id()
    key = level_id.lower()
    if key in level_ids():
        return key
    return default_level_id()
