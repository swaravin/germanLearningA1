from __future__ import annotations

import contextlib
import os
import re
from urllib.parse import quote

import requests

from a1.articles import (
    article_for_german,
    default_example_sentences,
    example_word_label,
    german_accusative,
    german_with_article,
)

_PROXY_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
    "SOCKS_PROXY",
    "SOCKS5_PROXY",
    "socks_proxy",
    "socks5_proxy",
)

_SESSION = requests.Session()
_SESSION.trust_env = False
_SESSION.headers["User-Agent"] = "A1GermanFlashcards/1.0 (educational lookup)"


class LookupError(RuntimeError):
    """Raised when an online lookup fails."""


@contextlib.contextmanager
def _without_proxy_env():
    saved: dict[str, str] = {}
    for key in _PROXY_KEYS:
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    try:
        yield
    finally:
        os.environ.update(saved)


def _clean_translation(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    # MyMemory sometimes adds trailing metadata
    if "MYMEMORY WARNING" in text.upper():
        text = text.split("MYMEMORY WARNING")[0].strip()
    return text


def _translate_mymemory(text: str, source: str, target: str) -> str:
    with _without_proxy_env():
        response = _SESSION.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"{source}|{target}"},
            timeout=20,
        )
    if response.status_code != 200:
        raise LookupError("MyMemory translation failed.")
    data = response.json()
    if data.get("responseStatus") != 200:
        raise LookupError(data.get("responseDetails") or "MyMemory translation failed.")
    result = _clean_translation(data.get("responseData", {}).get("translatedText", ""))
    if not result:
        raise LookupError("MyMemory returned an empty translation.")
    return result


def _translate_lingva(text: str, source: str, target: str) -> str:
    with _without_proxy_env():
        response = _SESSION.get(
            f"https://lingva.ml/api/v1/{source}/{target}/{quote(text)}",
            timeout=20,
        )
    if response.status_code != 200:
        raise LookupError("Lingva translation failed.")
    result = _clean_translation(response.json().get("translation", ""))
    if not result:
        raise LookupError("Lingva returned an empty translation.")
    return result


def translate_text(text: str, source: str, target: str) -> str:
    """Translate text between de and en using online services."""
    text = text.strip()
    if not text:
        raise LookupError("Enter text first.")
    if source not in {"de", "en"} or target not in {"de", "en"} or source == target:
        raise LookupError("Translation supports German ↔ English only.")

    errors: list[str] = []
    for fetcher in (_translate_mymemory, _translate_lingva):
        try:
            return fetcher(text, source, target)
        except (LookupError, requests.RequestException) as exc:
            errors.append(str(exc))

    raise LookupError(
        "Could not translate online. Use the browser lookup button or check your connection."
        + (f" ({errors[-1]})" if errors else "")
    )


def translate_word_de_to_en(german: str) -> str:
    return translate_text(german, "de", "en")


def translate_word_en_to_de(english: str) -> str:
    return translate_text(english, "en", "de")


def lookup_in_vocabulary(
    words: list,
    *,
    german: str = "",
    english: str = "",
) -> tuple[str, str] | None:
    """Find a word in the loaded deck (built-in + custom cards)."""
    from a1.vocab import Word, english_short

    if german.strip():
        key = german.strip().lower()
        for w in words:
            if isinstance(w, Word) and w.german.strip().lower() == key:
                return w.german, english_short(w.english)

    if english.strip():
        key = english_short(english).lower()
        for w in words:
            if not isinstance(w, Word):
                continue
            en = english_short(w.english)
            if en.lower() == key or key in w.english.lower():
                return w.german, en

    return None


def _tatoeba_sentence_translations(sentence_id: int) -> list[str]:
    with _without_proxy_env():
        response = _SESSION.get(
            f"https://tatoeba.org/en/api_v0/sentence_translations/{sentence_id}",
            timeout=20,
        )
    if response.status_code != 200:
        return []
    data = response.json()
    out: list[str] = []
    for item in data.get("results", []):
        text = _clean_translation(item.get("text", ""))
        lang = item.get("lang", "")
        if text and lang in {"eng", "en"}:
            out.append(text)
    return out


def fetch_example_sentences(
    german: str,
    english: str = "",
    *,
    limit: int = 5,
) -> list[tuple[str, str]]:
    """Return (German, English) example sentence pairs from Tatoeba."""
    german = german.strip()
    if not german:
        raise LookupError("Enter a German word first.")

    query = german
    with _without_proxy_env():
        response = _SESSION.get(
            "https://tatoeba.org/en/api_v0/search",
            params={
                "from": "deu",
                "to": "eng",
                "query": query,
                "sort": "relevance",
            },
            timeout=25,
        )
    if response.status_code != 200:
        raise LookupError("Tatoeba sentence search failed.")

    pairs: list[tuple[str, str]] = []
    for item in response.json().get("results", []):
        if item.get("lang") not in {"deu", "de"}:
            continue
        de_text = _clean_translation(item.get("text", ""))
        if not de_text or german.lower() not in de_text.lower():
            continue

        en_candidates = _tatoeba_sentence_translations(int(item["id"]))
        if not en_candidates and english:
            try:
                en_candidates = [translate_text(de_text, "de", "en")]
            except LookupError:
                continue
        for en_text in en_candidates:
            en_text = _clean_translation(en_text)
            if de_text and en_text:
                pairs.append((de_text, en_text))
                break
        if len(pairs) >= limit:
            break

    if pairs:
        return pairs

    # Fallback: template sentences (includes der/die/das on nouns).
    if english.strip():
        de, en = default_example_sentences(german, english)
        return [(de, en)]

    art = article_for_german(german)
    label = example_word_label(german, article=art)
    templates_de = [
        f"Das Wort ist „{label}“.",
        f"Das ist {german_with_article(german, article=art) if art else german}.",
        f"Ich kenne das Wort „{label}“.",
    ]
    if art:
        templates_de.append(f"Ich brauche {german_accusative(german, article=art)}.")

    for de_text in templates_de:
        try:
            en_text = translate_text(de_text, "de", "en")
            pairs.append((de_text, en_text))
            if len(pairs) >= limit:
                break
        except LookupError:
            continue

    if not pairs:
        raise LookupError("No example sentences found online.")
    return pairs


def best_example_sentence(
    german: str,
    english: str = "",
    *,
    section: str = "",
    article: str = "",
) -> tuple[str, str]:
    german = german.strip()
    art = article_for_german(german, section=section, stored=article)
    try:
        pairs = fetch_example_sentences(german, english, limit=3)
    except LookupError:
        pairs = []

    if not pairs:
        return default_example_sentences(german, english, section=section, article=article)

    if art:
        labeled = german_with_article(german, article=art)
        for de, en in pairs:
            if labeled in de or german_accusative(german, article=art) in de:
                return de, en
        return default_example_sentences(german, english, section=section, article=article)

    return pairs[0]
