#!/usr/bin/env python3
"""Export vocabulary.json for the A1 flashcard app."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from a1.articles import article_for_german, german_with_article
from a1.config import DATA_DIR, VOCAB_JSON
from a1.image_lookup import IMAGE_LOOKUP
from a1.images import image_queries_for
from build_german_vocab_learn_pack import collect_entries


def main() -> None:
    words = []
    for e in collect_entries():
        queries = image_queries_for(e.german, e.english)
        q = queries[0] if queries else ""
        has_img = bool(queries) or e.german in IMAGE_LOOKUP
        art = article_for_german(e.german, section=e.section)
        de_label = german_with_article(e.german, section=e.section, article=art)
        words.append(
            {
                "id": e.index,
                "section": e.section,
                "german": e.german,
                "english": e.english,
                "pronunciation": de_label if art else e.pronunciation,
                "sentence_de": e.sentence_de,
                "sentence_en": e.sentence_en,
                "image_query": q,
                "has_image": has_img,
                **({"article": art} if art else {}),
            }
        )
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    VOCAB_JSON.write_text(
        json.dumps({"words": words}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(words)} words to {VOCAB_JSON}")


if __name__ == "__main__":
    main()
