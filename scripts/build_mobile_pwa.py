#!/usr/bin/env python3
"""Sync CEFR level word lists into mobile/data/ for the offline PWA."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOBILE_DATA = ROOT / "mobile" / "data"

import sys

sys.path.insert(0, str(ROOT))

from a1.levels import LEVELS_MANIFEST, all_levels, custom_vocabulary_path, ensure_level_layout, level_dir, vocabulary_path


def _write_sw_cache(level_ids: list[str]) -> None:
    import re

    assets = [
        "./",
        "./index.html",
        "./css/app.css",
        "./js/app.js",
        "./manifest.json",
        "./data/levels.json",
    ]
    for lid in level_ids:
        assets.append(f"./data/levels/{lid}/vocabulary.json")
        assets.append(f"./data/levels/{lid}/custom_vocabulary.json")
    sw_path = ROOT / "mobile" / "sw.js"
    text = sw_path.read_text(encoding="utf-8")
    match = re.search(r'const CACHE = "(de-learn-v\d+)";', text)
    cache_line = f'const CACHE = "{match.group(1)}";' if match else 'const CACHE = "de-learn-v11";'
    if 'const CACHE = "' not in text:
        raise RuntimeError("sw.js CACHE line not found")
    text = text.split('const CACHE = "')[0] + cache_line + "\n"
    assets_js = ",\n  ".join(json.dumps(a) for a in assets)
    text = text.split("const ASSETS = [", 1)[0] + f"const ASSETS = [\n  {assets_js},\n];\n"
    rest = sw_path.read_text(encoding="utf-8").split("];", 1)[1]
    text += rest
    sw_path.write_text(text, encoding="utf-8")


def main() -> None:
    ensure_level_layout()
    MOBILE_DATA.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LEVELS_MANIFEST, MOBILE_DATA / "levels.json")

    level_ids: list[str] = []
    for lv in all_levels():
        level_ids.append(lv.id)
        dest = MOBILE_DATA / "levels" / lv.id
        dest.mkdir(parents=True, exist_ok=True)
        for src_name, dst_name in (
            ("vocabulary.json", "vocabulary.json"),
            ("custom_vocabulary.json", "custom_vocabulary.json"),
        ):
            src = level_dir(lv.id) / src_name
            dst = dest / dst_name
            if src.exists():
                shutil.copy2(src, dst)
            elif dst_name == "custom_vocabulary.json":
                dst.write_text(json.dumps({"words": []}, indent=2) + "\n", encoding="utf-8")
        vocab = vocabulary_path(lv.id)
        if not vocab.exists() or vocab.stat().st_size < 10:
            print(f"Warning: missing vocabulary for {lv.id} — run export/seed script")

    _write_sw_cache(level_ids)
    print(f"Synced {len(level_ids)} CEFR level(s) → {MOBILE_DATA}")


if __name__ == "__main__":
    main()
