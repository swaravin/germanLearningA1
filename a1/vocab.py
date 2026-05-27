from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from a1.config import CUSTOM_SECTION, CUSTOM_VOCAB_JSON, DATA_DIR, VOCAB_JSON
from a1.images import image_queries_for
from a1.articles import article_for_german, default_example_sentences, german_with_article


@dataclass
class Word:
    id: int
    section: str
    german: str
    english: str
    pronunciation: str
    sentence_de: str
    sentence_en: str
    image_query: str
    has_image: bool
    article: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> Word:
        german = str(d["german"])
        section = str(d["section"])
        stored_article = str(d.get("article", "")).strip().lower()
        article = stored_article if stored_article in ("der", "die", "das") else article_for_german(
            german, section=section, stored=stored_article
        )
        return cls(
            id=int(d["id"]),
            section=section,
            german=german,
            english=str(d["english"]),
            pronunciation=str(d.get("pronunciation", "")),
            sentence_de=str(d.get("sentence_de", "")),
            sentence_en=str(d.get("sentence_en", "")),
            image_query=str(d.get("image_query", "")),
            has_image=bool(d.get("has_image", False)),
            article=article,
        )

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "section": self.section,
            "german": self.german,
            "english": self.english,
            "pronunciation": self.pronunciation,
            "sentence_de": self.sentence_de,
            "sentence_en": self.sentence_en,
            "image_query": self.image_query,
            "has_image": self.has_image,
        }
        if self.article:
            d["article"] = self.article
        return d


def english_short(en: str) -> str:
    return en.split(" / ")[0].split(" (")[0].strip()


def load_vocabulary(path: Path | None = None) -> list[Word]:
    p = path or VOCAB_JSON
    raw = json.loads(p.read_text(encoding="utf-8"))
    return [Word.from_dict(item) for item in raw["words"]]


def load_custom_vocabulary() -> list[Word]:
    if not CUSTOM_VOCAB_JSON.exists():
        return []
    raw = json.loads(CUSTOM_VOCAB_JSON.read_text(encoding="utf-8"))
    return [Word.from_dict(item) for item in raw.get("words", [])]


def save_custom_vocabulary(words: list[Word]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_VOCAB_JSON.write_text(
        json.dumps({"words": [w.to_dict() for w in words]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _all_word_ids() -> list[int]:
    ids: list[int] = []
    for path in (VOCAB_JSON, CUSTOM_VOCAB_JSON):
        if not path.exists():
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        ids.extend(int(w["id"]) for w in raw.get("words", []))
    return ids


def vocabulary_revision() -> tuple[float, float]:
    """File mtimes used to detect vocabulary changes."""
    v = VOCAB_JSON.stat().st_mtime if VOCAB_JSON.exists() else 0.0
    c = CUSTOM_VOCAB_JSON.stat().st_mtime if CUSTOM_VOCAB_JSON.exists() else 0.0
    return v, c


def load_all_vocabulary() -> list[Word]:
    return load_vocabulary() + load_custom_vocabulary()


def custom_word_ids() -> set[int]:
    return {w.id for w in load_custom_vocabulary()}


def is_custom_word(word_id: int) -> bool:
    return word_id in custom_word_ids()


def get_custom_word(word_id: int) -> Word | None:
    for w in load_custom_vocabulary():
        if w.id == word_id:
            return w
    return None


def update_custom_word(
    word_id: int,
    german: str,
    english: str,
    *,
    section: str = CUSTOM_SECTION,
    pronunciation: str = "",
    sentence_de: str = "",
    sentence_en: str = "",
    article: str = "",
) -> Word:
    german = german.strip()
    english = english.strip()
    if not german or not english:
        raise ValueError("German and English are required.")

    custom = load_custom_vocabulary()
    idx = next((i for i, w in enumerate(custom) if w.id == word_id), None)
    if idx is None:
        raise ValueError("Card not found.")

    old = custom[idx]
    queries = image_queries_for(german, english)
    resolved_article = article_for_german(german, section=section.strip() or old.section, stored=article)
    de_label = german_with_article(german, article=resolved_article)
    default_de, default_en = default_example_sentences(
        german, english, section=section.strip() or old.section, article=resolved_article
    )
    word = Word(
        id=word_id,
        section=section.strip() or old.section or CUSTOM_SECTION,
        german=german,
        english=english,
        pronunciation=pronunciation.strip() or de_label,
        sentence_de=sentence_de.strip() or default_de,
        sentence_en=sentence_en.strip() or default_en,
        image_query=queries[0] if queries else old.image_query,
        has_image=bool(queries) or old.has_image,
        article=resolved_article,
    )
    custom[idx] = word
    save_custom_vocabulary(custom)
    return word


def delete_custom_word(word_id: int) -> bool:
    custom = load_custom_vocabulary()
    kept = [w for w in custom if w.id != word_id]
    if len(kept) == len(custom):
        return False
    save_custom_vocabulary(kept)
    return True


def add_custom_word(
    german: str,
    english: str,
    *,
    section: str = CUSTOM_SECTION,
    pronunciation: str = "",
    sentence_de: str = "",
    sentence_en: str = "",
    article: str = "",
) -> Word:
    german = german.strip()
    english = english.strip()
    if not german or not english:
        raise ValueError("German and English are required.")

    queries = image_queries_for(german, english)
    resolved_article = article_for_german(german, section=section, stored=article)
    de_label = german_with_article(german, article=resolved_article)
    default_de, default_en = default_example_sentences(
        german, english, section=section, article=resolved_article
    )
    word = Word(
        id=max(_all_word_ids(), default=0) + 1,
        section=section.strip() or CUSTOM_SECTION,
        german=german,
        english=english,
        pronunciation=pronunciation.strip() or de_label,
        sentence_de=sentence_de.strip() or default_de,
        sentence_en=sentence_en.strip() or default_en,
        image_query=queries[0] if queries else "",
        has_image=bool(queries),
        article=resolved_article,
    )
    custom = load_custom_vocabulary()
    custom.append(word)
    save_custom_vocabulary(custom)
    return word


def sections(words: list[Word]) -> list[str]:
    seen: list[str] = []
    for w in words:
        if w.section not in seen:
            seen.append(w.section)
    return seen


def filter_words(
    words: list[Word],
    section: str | None = None,
    with_images_only: bool = False,
) -> list[Word]:
    out = words
    if section and section != "All sections":
        out = [w for w in out if w.section == section]
    if with_images_only:
        out = [w for w in out if w.has_image]
    return out


def shuffle_deck(words: list[Word]) -> list[Word]:
    deck = list(words)
    random.shuffle(deck)
    return deck


def search_words(words: list[Word], query: str) -> list[Word]:
    q = query.strip().lower()
    if not q:
        return words
    out: list[Word] = []
    for w in words:
        haystack = " ".join(
            (
                w.german,
                w.english,
                w.pronunciation,
                w.sentence_de,
                w.sentence_en,
                w.section,
                w.article,
                german_with_article(w.german, section=w.section, article=w.article),
            )
        ).lower()
        if q in haystack:
            out.append(w)
    return out
