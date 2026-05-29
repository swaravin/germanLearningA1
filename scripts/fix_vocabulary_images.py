#!/usr/bin/env python3
"""Refresh has_image / image_query in level vocab JSON and remove stale cached pictures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from a1.config import IMAGES_DIR
from a1.images import image_path, image_queries_for
from a1.levels import all_levels, ensure_level_layout, vocabulary_path


def fix_level(level_id: str) -> tuple[int, int, int]:
    path = vocabulary_path(level_id)
    if not path.exists():
        print(f"  skip {level_id}: no {path}")
        return 0, 0, 0

    data = json.loads(path.read_text(encoding="utf-8"))
    words = data.get("words", [])
    changed = 0
    enabled = 0

    for w in words:
        queries = image_queries_for(w["german"], w["english"], section=w.get("section", ""))
        new_query = queries[0] if queries else ""
        new_flag = bool(queries)
        old_query = w.get("image_query", "")
        old_flag = w.get("has_image", False)
        query_changed = old_flag and new_flag and old_query != new_query
        if old_query != new_query or old_flag != new_flag:
            changed += 1
        w["image_query"] = new_query
        w["has_image"] = new_flag
        if new_flag:
            enabled += 1
        w["_purge_image"] = (not new_flag) or query_changed or new_flag

    path.write_text(json.dumps({"words": words}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    valid_ids = {w["id"] for w in words if w.get("has_image")}
    removed = 0
    if IMAGES_DIR.exists():
        for w in words:
            if not w.pop("_purge_image", False):
                continue
            img = image_path(w["id"])
            if img.exists():
                img.unlink(missing_ok=True)
                removed += 1
        for img in IMAGES_DIR.glob("*.jpg"):
            try:
                wid = int(img.stem)
            except ValueError:
                continue
            if wid not in valid_ids:
                img.unlink(missing_ok=True)
                removed += 1

    path.write_text(json.dumps({"words": words}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"  {level_id}: {len(words)} words, {enabled} with images, {changed} metadata updates, {removed} stale files removed")
    return len(words), enabled, removed


def main() -> None:
    ensure_level_layout()
    levels = [lv.id for lv in all_levels()]
    print(f"Fixing image metadata under {IMAGES_DIR} …")
    total_removed = 0
    for lid in levels:
        _, _, removed = fix_level(lid)
        total_removed += removed
    print(f"Done. Removed {total_removed} orphaned image file(s).")
    print("Re-open flashcards — nouns will fetch fresh images on demand.")


if __name__ == "__main__":
    main()
