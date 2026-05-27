from __future__ import annotations

import re

# German definite articles for A1 nouns (lemma → der | die | das).
NOUN_ARTICLES: dict[str, str] = {
    # 8. Family & People
    "Mutter": "die",
    "Vater": "der",
    "Eltern": "die",
    "Kind": "das",
    "Kinder": "die",
    "Sohn": "der",
    "Tochter": "die",
    "Bruder": "der",
    "Schwester": "die",
    "Großmutter": "die",
    "Großvater": "der",
    "Oma": "die",
    "Opa": "der",
    "Familie": "die",
    "Mann": "der",
    "Frau": "die",
    "Freund": "der",
    "Freundin": "die",
    "Nachbar": "der",
    "Kollege": "der",
    "Kollegin": "die",
    "Chef": "der",
    "Lehrer": "der",
    "Lehrerin": "die",
    "Mensch": "der",
    "Leute": "die",
    "Name": "der",
    "Alter": "das",
    "Geburtsdatum": "das",
    "Adresse": "die",
    # 9. Home & Objects
    "Haus": "das",
    "Wohnung": "die",
    "Zimmer": "das",
    "Küche": "die",
    "Bad": "das",
    "Toilette": "die",
    "Wohnzimmer": "das",
    "Schlafzimmer": "das",
    "Balkon": "der",
    "Garten": "der",
    "Garage": "die",
    "Tisch": "der",
    "Stuhl": "der",
    "Bett": "das",
    "Sofa": "das",
    "Schrank": "der",
    "Regal": "das",
    "Tür": "die",
    "Fenster": "das",
    "Wand": "die",
    "Boden": "der",
    "Dach": "das",
    "Schlüssel": "der",
    "Lampe": "die",
    "Uhr": "die",
    "Bild": "das",
    "Teppich": "der",
    "Handy": "das",
    "Telefon": "das",
    "Computer": "der",
    "Laptop": "der",
    "Tablet": "das",
    "Buch": "das",
    "Zeitung": "die",
    "Stift": "der",
    "Papier": "das",
    "Tasche": "die",
    "Geld": "das",
    "Karte": "die",
    # 10. Food & Drinks
    "Essen": "das",
    "Frühstück": "das",
    "Mittagessen": "das",
    "Abendessen": "das",
    "Brot": "das",
    "Butter": "die",
    "Käse": "der",
    "Milch": "die",
    "Joghurt": "der",
    "Wasser": "das",
    "Saft": "der",
    "Kaffee": "der",
    "Tee": "der",
    "Fleisch": "das",
    "Fisch": "der",
    "Reis": "der",
    "Nudeln": "die",
    "Kartoffel": "die",
    "Obst": "das",
    "Gemüse": "das",
    "Apfel": "der",
    "Banane": "die",
    "Orange": "die",
    "Tomate": "die",
    "Salat": "der",
    "Zwiebel": "die",
    "Zucker": "der",
    "Salz": "das",
    "Öl": "das",
    "Suppe": "die",
    # 11. Places
    "Stadt": "die",
    "Dorf": "das",
    "Land": "das",
    "Straße": "die",
    "Supermarkt": "der",
    "Markt": "der",
    "Laden": "der",
    "Geschäft": "das",
    "Bank": "die",
    "Post": "die",
    "Schule": "die",
    "Universität": "die",
    "Krankenhaus": "das",
    "Arzt": "der",
    "Apotheke": "die",
    "Hotel": "das",
    "Restaurant": "das",
    "Café": "das",
    "Bahnhof": "der",
    "Flughafen": "der",
    "Haltestelle": "die",
    "Park": "der",
    "Kino": "das",
    "Museum": "das",
    "Bibliothek": "die",
    "Kirche": "die",
    # 12. Transport & Travel
    "Auto": "das",
    "Bus": "der",
    "Zug": "der",
    "Fahrrad": "das",
    "Motorrad": "das",
    "Flugzeug": "das",
    "Ticket": "das",
    "Fahrkarte": "die",
    "Reise": "die",
    "Urlaub": "der",
    "Gepäck": "das",
    "Koffer": "der",
    "Weg": "der",
    "Richtung": "die",
    "Stadtplan": "der",
    # 13. Time & Dates (nouns only)
    "Tag": "der",
    "Woche": "die",
    "Monat": "der",
    "Jahr": "das",
    "Morgen": "der",
    "Abend": "der",
    "Nacht": "die",
    "Stunde": "die",
    "Minute": "die",
    "Sekunde": "die",
    "Montag": "der",
    "Dienstag": "der",
    "Mittwoch": "der",
    "Donnerstag": "der",
    "Freitag": "der",
    "Samstag": "der",
    "Sonntag": "der",
    "Januar": "der",
    "Februar": "der",
    "März": "der",
    "April": "der",
    "Mai": "der",
    "Juni": "der",
    "Juli": "der",
    "August": "der",
    "September": "der",
    "Oktober": "der",
    "November": "der",
    "Dezember": "der",
    # Custom / extras
    "Schiff": "das",
    "Ort": "der",
    "Hund": "der",
    "Katze": "die",
}

_NO_ARTICLE_SECTIONS = (
    "1. Personal Pronouns",
    "2. Articles & Possessives",
    "3. Basic Everyday Words",
    "4. Question Words",
    "5. Prepositions",
    "6. Numbers (0–100)",
    "7. Essential Verbs",
    "14. Adjectives",
    "15. Useful Adverbs & Words",
)

_VALID = frozenset({"der", "die", "das"})


def _lemma(german: str) -> str:
    parts = german.strip().split()
    return parts[0] if parts else ""


def _guess_article(german: str) -> str:
    """Best-effort guess for unknown capitalized nouns (custom cards)."""
    word = _lemma(german)
    if not word or not word[0].isupper():
        return ""
    if word in NOUN_ARTICLES:
        return NOUN_ARTICLES[word]
    lower = word.lower()
    if lower.endswith(("ung", "heit", "keit", "schaft", "tät", "ion")):
        return "die"
    if lower.endswith(("chen", "lein", "ment", "um")):
        return "das"
    if lower.endswith("er") and len(word) > 3:
        return "der"
    return ""


def article_for_german(german: str, *, section: str = "", stored: str = "") -> str:
    """Return der | die | das, or empty string if not a noun."""
    stored = (stored or "").strip().lower()
    if stored in ("-", "none", "no"):
        return ""
    if stored in _VALID:
        return stored

    if section and any(section.startswith(p) for p in _NO_ARTICLE_SECTIONS):
        lemma = _lemma(german)
        if lemma in NOUN_ARTICLES:
            return NOUN_ARTICLES[lemma]
        return ""

    lemma = _lemma(german)
    if lemma in NOUN_ARTICLES:
        return NOUN_ARTICLES[lemma]

    # Try title case for custom entries like "weg" → "Weg"
    titled = lemma[:1].upper() + lemma[1:] if lemma else ""
    if titled in NOUN_ARTICLES:
        return NOUN_ARTICLES[titled]

    return _guess_article(german)


def article_for_word(word) -> str:
    """Resolve article for a Word dataclass or dict-like object."""
    stored = getattr(word, "article", "") or (word.get("article", "") if isinstance(word, dict) else "")
    return article_for_german(
        getattr(word, "german", "") or word.get("german", ""),
        section=getattr(word, "section", "") or word.get("section", ""),
        stored=stored,
    )


def german_with_article(german: str, *, section: str = "", article: str = "") -> str:
    art = article_for_german(german, section=section, stored=article)
    if not art:
        return german.strip()
    lemma = _lemma(german)
    rest = german.strip()[len(lemma) :].strip()
    if rest:
        return f"{art} {lemma} {rest}".strip()
    return f"{art} {lemma}"


def german_with_article_word(word) -> str:
    art = article_for_word(word)
    if not art:
        return word.german.strip()
    return german_with_article(word.german, article=art)


def german_de_speech(word) -> str:
    """German text for TTS (includes article when known)."""
    return german_with_article_word(word)


def pronunciation_display(word) -> str:
    pron = (word.pronunciation or "").strip()
    if pron and pron != word.german.strip():
        return pron
    return german_with_article_word(word)


_ACCUSATIVE = {"der": "den", "die": "die", "das": "das"}


def german_accusative(german: str, *, section: str = "", article: str = "") -> str:
    art = article_for_german(german, section=section, stored=article)
    if not art:
        return german.strip()
    acc = _ACCUSATIVE.get(art, art)
    lemma = _lemma(german)
    rest = german.strip()[len(lemma) :].strip()
    if rest:
        return f"{acc} {lemma} {rest}".strip()
    return f"{acc} {lemma}"


def _english_short(en: str) -> str:
    return en.split(" / ")[0].split(" (")[0].strip()


def default_example_sentences(
    german: str,
    english: str,
    *,
    section: str = "",
    article: str = "",
) -> tuple[str, str]:
    """Build default DE/EN example sentences (with der/die/das on nouns)."""
    de = german.strip()
    en_short = _english_short(english)
    sec = section.lower()
    art = article_for_german(de, section=section, stored=article)

    if section.startswith("6."):
        return (f"Die Zahl ist {de}.", f"The number is {en_short}.")
    if "pronoun" in sec or section.startswith("1."):
        return (
            f"Das Wort ist „{de}“. Das bedeutet: {en_short}.",
            f'The word is "{de}". It means: {en_short}.',
        )
    if section.startswith("7."):
        return (
            f"Das Verb ist „{de}“. Beispiel: Ich kann {de}.",
            f'The verb is "{de}". Example: I can {en_short}.',
        )
    if section.startswith("14.") or section.startswith("15."):
        return (
            f"„{de}“ bedeutet „{en_short}“. Das ist {de}.",
            f'"{de}" means "{en_short}". That is {en_short}.',
        )
    if section.startswith("5.") or section.startswith("2.") or section.startswith("4."):
        return (
            f"Wir lernen: „{de}“. Auf Englisch: {en_short}.",
            f'We learn: "{de}". In English: {en_short}.',
        )
    if art:
        nom = german_with_article(de, article=art)
        acc = german_accusative(de, article=art)
        return (
            f"Das ist {nom}. Ich brauche {acc}.",
            f"This is {en_short}. I need {en_short}.",
        )
    if de[:1].isupper() and de not in ("Sie",):
        return (
            f"Das ist {de}. Ich brauche {de}.",
            f"This is {en_short}. I need {en_short}.",
        )
    return (
        f"„{de}“ — auf Englisch: {en_short}.",
        f'"{de}" — in English: {en_short}.',
    )


def example_word_label(german: str, *, section: str = "", article: str = "") -> str:
    """Short label for 'Das Wort ist …' templates."""
    art = article_for_german(german, section=section, stored=article)
    if art:
        return german_with_article(german, article=art)
    return german.strip()


def normalize_example_sentences(
    german: str,
    english: str,
    de: str,
    en: str,
    *,
    section: str = "",
    article: str = "",
) -> tuple[str, str]:
    """Prefer sentences that include der/die/das when the word is a noun."""
    art = article_for_german(german, section=section, stored=article)
    if not art:
        return de, en
    labeled = german_with_article(german, article=art)
    acc = german_accusative(german, article=art)
    if labeled in de or acc in de:
        return de, en
    return default_example_sentences(german, english, section=section, article=article)
