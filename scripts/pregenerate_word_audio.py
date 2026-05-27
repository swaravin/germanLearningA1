#!/usr/bin/env python3
"""Pre-generate per-word audio clips (run while online)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from a1.audio import ensure_audio_sync
from a1.vocab import load_all_vocabulary


def main() -> None:
    words = load_all_vocabulary()
    ok = 0
    failed: list[str] = []
    for w in words:
        try:
            ensure_audio_sync(w.id, w.german, w.english, article=w.article, section=w.section)
            ok += 1
            print(f"OK  {w.id:04d} {w.german} / {w.english}")
        except Exception as exc:
            failed.append(f"{w.german}: {exc}")
            print(f"FAIL {w.id:04d} {w.german}: {exc}")
    print(f"\nGenerated {ok}/{len(words)} words.")
    if failed:
        print(f"{len(failed)} failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
