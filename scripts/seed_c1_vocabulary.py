#!/usr/bin/env python3
"""Import data/drafts/c1_vocabulary_exhaustive.csv → data/levels/c1/vocabulary.json."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from a1.articles import article_for_german, german_with_article
from a1.images import image_queries_for
from a1.levels import ensure_level_layout, vocabulary_path

CSV_PATH = ROOT / "data" / "drafts" / "c1_vocabulary_exhaustive.csv"


def _english_short(english: str) -> str:
    return english.split("(")[0].strip().rstrip(".")


def _is_phrase(german: str) -> bool:
    g = german.strip()
    if len(g) > 55:
        return True
    if g.endswith(",") or "…" in g:
        return True
    phrase_starts = (
        "Ich ",
        "Es ",
        "Man ",
        "Die ",
        "Der ",
        "Das ",
        "Ein ",
        "Eine ",
        "In ",
        "Angesichts ",
        "Immer ",
        "Vor ",
        "Zunehmend ",
        "Mit ",
        "Aus ",
        "Was ",
        "Lassen ",
        "Meiner ",
        "Meines ",
        "Zusammenfassend ",
        "Abschließend ",
        "Alles ",
        "Unterm ",
        "Letztlich ",
        "Guten ",
        "Sehr geehrte",
        "Sehr geehrter ",
        "Bezugnehmend ",
        "Hiermit ",
        "Leider ",
        "Könnten ",
        "Für ",
        "Wie ",
        "Gibt ",
        "Darauf ",
        "Demgegenüber ",
        "Zwar ",
        "Gegner ",
        "Kritiker ",
        "Trotz ",
        "Nicht ",
        "Darüber ",
        "Des Weiteren ",
        "Obgleich ",
        "Angenommen ",
        "Falls ",
        "Hätte ",
        "Zunächst ",
        "Im ",
        "Anschließend ",
        "Nun ",
        "Wie bereits ",
        "Gegenwärtig ",
    )
    return any(g.startswith(p) for p in phrase_starts)


def _sentence_pair(german: str, english: str) -> tuple[str, str]:
    en = _english_short(english)
    if _is_phrase(german):
        de = german if german.endswith((".", "…", "!", "?")) else german.rstrip(",") + " …"
        return de, english if english.endswith(".") else english + "."
    return (
        f"{german} ({en}).",
        f"{german} ({en}).",
    )


def load_csv_entries() -> list[tuple[str, str, str]]:
    if not CSV_PATH.exists():
        raise SystemExit(
            f"Missing {CSV_PATH}\nRun: python scripts/build_c1_vocabulary_draft.py"
        )
    rows: list[tuple[str, str, str]] = []
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            section = (row.get("section") or "").strip()
            german = (row.get("german") or "").strip()
            english = (row.get("english") or "").strip()
            if section and german and english:
                rows.append((section, german, english))
    return rows


def build_words(entries: list[tuple[str, str, str]]) -> list[dict]:
    words: list[dict] = []
    for i, (section, german, english) in enumerate(entries, start=1):
        art = article_for_german(german, section=section)
        de_label = german_with_article(german, article=art)
        queries = image_queries_for(german, english, section=section)
        sent_de, sent_en = _sentence_pair(german, english)
        entry: dict = {
            "id": i,
            "section": section,
            "german": german,
            "english": english,
            "pronunciation": de_label if art and " " not in german.strip() else german,
            "sentence_de": sent_de,
            "sentence_en": sent_en,
            "image_query": queries[0] if queries else "",
            "has_image": bool(queries),
        }
        if art and " " not in german.strip():
            entry["article"] = art
        words.append(entry)
    return words


def main() -> None:
    ensure_level_layout()
    entries = load_csv_entries()
    words = build_words(entries)
    out = vocabulary_path("c1")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"words": words}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with_img = sum(1 for w in words if w.get("has_image"))
    print(f"Wrote {len(words)} C1 words ({with_img} with images) → {out}")


if __name__ == "__main__":
    main()
