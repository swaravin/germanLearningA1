#!/usr/bin/env python3
"""Copy vocabulary into mobile/data/ for the offline iPhone PWA."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOBILE_DATA = ROOT / "mobile" / "data"
VOCAB = ROOT / "data" / "vocabulary.json"
CUSTOM = ROOT / "data" / "custom_vocabulary.json"


def main() -> None:
    MOBILE_DATA.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VOCAB, MOBILE_DATA / "vocabulary.json")
    if CUSTOM.exists():
        shutil.copy2(CUSTOM, MOBILE_DATA / "custom_vocabulary.json")
    else:
        (MOBILE_DATA / "custom_vocabulary.json").write_text(
            json.dumps({"words": []}, indent=2), encoding="utf-8"
        )
    print(f"Synced vocabulary → {MOBILE_DATA}")


if __name__ == "__main__":
    main()
