from __future__ import annotations

import re
from pathlib import Path

import requests

from a1.config import IMAGES_DIR
from a1.image_lookup import IMAGE_LOOKUP
from a1.articles import NOUN_ARTICLES

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "A1GermanFlashcards/1.0 (educational; contact: local)"

# Grammar / function words — skip web lookup (no useful picture).
ABSTRACT_WORDS = frozenset(
    {
        "ich",
        "du",
        "er",
        "sie",
        "es",
        "wir",
        "ihr",
        "Sie",
        "der",
        "die",
        "das",
        "den",
        "dem",
        "des",
        "ein",
        "eine",
        "einen",
        "einem",
        "einer",
        "eines",
        "kein",
        "keine",
        "keinen",
        "keinem",
        "keiner",
        "mein",
        "dein",
        "sein",
        "unser",
        "euer",
        "Ihr",
        "nicht",
        "auch",
        "noch",
        "schon",
        "sehr",
        "gern",
        "ja",
        "nein",
        "und",
        "oder",
        "aber",
        "denn",
        "weil",
        "dass",
        "wenn",
        "als",
        "ob",
        "mit",
        "von",
        "zu",
        "in",
        "an",
        "auf",
        "für",
        "bei",
        "nach",
        "aus",
        "über",
        "unter",
        "vor",
        "hinter",
        "neben",
        "zwischen",
        "ist",
        "sind",
        "war",
        "waren",
        "hat",
        "haben",
        "wird",
        "werden",
    }
)

# Sections where flashcard images are misleading (verbs, grammar, etc.)
_NO_IMAGE_SECTIONS = (
    "1. Personal Pronouns",
    "2. Articles & Possessives",
    "3. Basic Everyday Words",
    "4. Question Words",
    "5. Prepositions",
    "6. Numbers",
    "7. Essential Verbs",
    "14. Adjectives",
    "15. Useful Adverbs",
)

# Single English tokens that match wrong Wikipedia pages (May, Can, Know, …).
_AMBIGUOUS_ENGLISH = frozenset(
    {
        "a",
        "an",
        "as",
        "be",
        "by",
        "can",
        "do",
        "go",
        "he",
        "if",
        "in",
        "is",
        "it",
        "know",
        "like",
        "may",
        "must",
        "no",
        "ok",
        "or",
        "run",
        "so",
        "to",
        "up",
        "us",
        "we",
        "will",
        "work",
        "you",
        "big",
        "bad",
        "old",
        "new",
        "hot",
        "red",
        "arm",
        "art",
        "bar",
        "bat",
        "bear",
        "bill",
        "bow",
        "change",
        "close",
        "cook",
        "date",
        "die",
        "fair",
        "fast",
        "fine",
        "fire",
        "fit",
        "flat",
        "fly",
        "glass",
        "gold",
        "hand",
        "hard",
        "help",
        "iron",
        "jam",
        "jet",
        "kind",
        "last",
        "lead",
        "light",
        "long",
        "mail",
        "mark",
        "match",
        "mean",
        "mine",
        "miss",
        "park",
        "pass",
        "play",
        "plum",
        "post",
        "ring",
        "rock",
        "rose",
        "spring",
        "staff",
        "star",
        "stop",
        "table",
        "talk",
        "tap",
        "tie",
        "trip",
        "watch",
        "well",
        "yard",
    }
)

_VISUAL_SECTION_PREFIXES = (
    "8. Family",
    "9. Home",
    "10. Food",
    "11. Places",
    "12. Transport",
    "13. Time",
)


def english_short(en: str) -> str:
    return en.split(" / ")[0].split(" (")[0].strip()


def _lemma(german: str) -> str:
    return german.strip().split()[0] if german.strip() else ""


def should_have_image(german: str, english: str, section: str = "") -> bool:
    """Only concrete nouns / mapped lemmas get pictures — not verbs like kennen → 'know'."""
    if german in ABSTRACT_WORDS:
        return False
    if german in IMAGE_LOOKUP:
        return True
    lemma = _lemma(german)
    titled = lemma[:1].upper() + lemma[1:] if lemma else ""
    if lemma in NOUN_ARTICLES or titled in NOUN_ARTICLES:
        return True
    if section and any(section.startswith(p) for p in _NO_IMAGE_SECTIONS):
        return False
    short = english_short(english).lower()
    if short.startswith("to "):
        return False
    if section and any(section.startswith(p) for p in _VISUAL_SECTION_PREFIXES):
        if lemma and lemma[0].isupper():
            return True
    return False


def _wiki_title(text: str) -> str:
    return text.strip().replace(" ", "_")


def image_query_for(german: str, english: str) -> tuple[str, bool]:
    queries = image_queries_for(german, english)
    if not queries:
        return "", False
    return queries[0], True


def image_queries_for(german: str, english: str, section: str = "") -> list[str]:
    if not should_have_image(german, english, section):
        return []

    seen: set[str] = set()
    queries: list[str] = []

    def add(q: str) -> None:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            queries.append(q)

    if german in IMAGE_LOOKUP:
        add(IMAGE_LOOKUP[german])

    lemma = _lemma(german)
    if lemma and lemma[0].isupper():
        add(_wiki_title(lemma))
        add(lemma)

    short = english_short(english)
    if short:
        base = short.split("(")[0].strip()
        if base.lower().startswith("to "):
            base = base[3:].strip()
        primary = base.split(",")[0].strip().split("/")[0].strip()
        token = primary.lower()
        # Prefer multi-word English labels; skip ambiguous one-word queries.
        if " " in primary and len(primary) > 3:
            add(_wiki_title(primary))
        elif token not in _AMBIGUOUS_ENGLISH and len(primary) > 3:
            add(_wiki_title(primary))

    return queries


def image_path(word_id: int) -> Path:
    return IMAGES_DIR / f"{word_id:04d}.jpg"


def _download(url: str) -> bytes | None:
    try:
        img = SESSION.get(url, timeout=15)
        if img.status_code == 200 and len(img.content) > 500:
            return img.content
    except Exception:
        return None
    return None


def fetch_wikipedia_thumbnail(title: str, lang: str = "en") -> bytes | None:
    url = (
        f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
        + requests.utils.quote(title.replace(" ", "_"))
    )
    try:
        r = SESSION.get(url, timeout=12)
        if r.status_code != 200:
            return None
        thumb = (r.json().get("thumbnail") or {}).get("source")
        if not thumb:
            return None
        return _download(thumb)
    except Exception:
        return None


def fetch_commons_thumbnail(search: str) -> bytes | None:
    try:
        r = SESSION.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": search,
                "gsrlimit": 5,
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": 480,
                "format": "json",
            },
            timeout=15,
        )
        if r.status_code != 200:
            return None
        pages = r.json().get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = (page.get("thumbnail") or {}).get("source")
            if thumb:
                data = _download(thumb)
                if data:
                    return data
    except Exception:
        return None
    return None


def _fetch_image_for_query(query: str) -> bytes | None:
    for fetcher in (
        lambda q: fetch_wikipedia_thumbnail(q, "en"),
        lambda q: fetch_wikipedia_thumbnail(q, "de"),
        fetch_commons_thumbnail,
    ):
        data = fetcher(query)
        if data:
            return data
        # Commons often works better with spaces than underscores.
        if "_" in query:
            data = fetcher(query.replace("_", " "))
            if data:
                return data
    return None


def ensure_image(
    word_id: int,
    german: str,
    english: str,
    query: str = "",
    section: str = "",
) -> Path | None:
    """Fetch and cache a picture for a word (Wikipedia + Wikimedia Commons)."""
    if not should_have_image(german, english, section):
        return None

    path = image_path(word_id)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 500:
        return path

    queries = image_queries_for(german, english, section)
    if query and query not in queries:
        queries.insert(0, query)

    for q in queries:
        data = _fetch_image_for_query(q)
        if data:
            path.write_bytes(data)
            return path
    return None


def placeholder_svg(german: str, english: str) -> str:
    de = re.sub(r"[<>&\"']", "", german)[:40]
    en = re.sub(r"[<>&\"']", "", english_short(english))[:40]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="280">
  <rect width="100%" height="100%" fill="#f0f4f2"/>
  <text x="50%" y="42%" text-anchor="middle" font-size="28" fill="#0f3d2e" font-family="sans-serif">{de}</text>
  <text x="50%" y="58%" text-anchor="middle" font-size="18" fill="#555" font-family="sans-serif">{en}</text>
</svg>"""
