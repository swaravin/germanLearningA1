#!/usr/bin/env python3
"""Add article fields to vocabulary JSON and clear stale German audio clips."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from a1.articles import article_for_german, default_example_sentences, german_with_article
from a1.config import AUDIO_DIR, CUSTOM_VOCAB_JSON, VOCAB_JSON


def _patch_file(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    raw = json.loads(path.read_text(encoding="utf-8"))
    words = raw.get("words", [])
    updated = 0
    cleared = 0
    for item in words:
        german = str(item.get("german", ""))
        section = str(item.get("section", ""))
        art = article_for_german(german, section=section, stored=str(item.get("article", "")))
        old_art = str(item.get("article", "")).strip().lower()
        if art:
            item["article"] = art
            de_label = german_with_article(german, article=art)
            if item.get("pronunciation") in ("", german, de_label) or not item.get("pronunciation"):
                item["pronunciation"] = de_label
            sde, sen = default_example_sentences(
                german, str(item.get("english", "")), section=section, article=art
            )
            if item.get("sentence_de") != sde:
                item["sentence_de"] = sde
                item["sentence_en"] = sen
                updated += 1
            if art != old_art:
                for clip in AUDIO_DIR.glob(f"{int(item['id']):04d}_de.*"):
                    clip.unlink(missing_ok=True)
                    cleared += 1
        elif "article" in item:
            item.pop("article", None)
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return updated, cleared


def main() -> None:
    total_u = total_c = 0
    for path in (VOCAB_JSON, CUSTOM_VOCAB_JSON):
        if not path.exists():
            continue
        u, c = _patch_file(path)
        total_u += u
        total_c += c
        print(f"Patched {path.name}: {u} articles updated, {c} German clips cleared")
    print("Done. Re-run pregenerate_word_audio.py or rebuild full MP3 courses for new speech.")


if __name__ == "__main__":
    main()
