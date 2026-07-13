from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from a1.audio import (
    course_clip_path,
    ensure_course_clips,
    get_course_clip_path,
    get_word_audio_path,
    user_recorded_clip,
)
from a1.config import FULL_AUDIO_DIR, PAUSE_AFTER_WORD_SEC, PAUSE_DE_BEFORE_EN_SEC
from a1.levels import custom_vocabulary_path, vocabulary_path
from a1.vocab import Word, load_all_vocabulary, load_custom_vocabulary, vocabulary_revision

COURSE_FILES = {
    "de_en": "German_A1_Audio_German_and_English.mp3",
    "en_de": "German_A1_Audio_English_and_German.mp3",
    "de_only": "German_A1_Audio_German_only.mp3",
}

EXTENDED_MARKER = "_with_my_cards"
CLIPS_MARKER = "_from_clips"
PLUS_CUSTOM_MARKER = "_plus_custom"

MODE_LABELS = {
    "de_en": "German → English",
    "en_de": "English → German",
    "de_only": "German only",
}


def _ffmpeg() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _vocab_signature() -> str:
    v, c = vocabulary_revision("a1")
    return hashlib.sha256(f"{v}:{c}".encode()).hexdigest()[:16]


def _custom_signature() -> str:
    path = custom_vocabulary_path("a1")
    if not path.exists():
        return "none"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def invalidate_extended_courses() -> None:
    """Drop cached full-course MP3s built from custom or clip merges."""
    if not FULL_AUDIO_DIR.exists():
        return
    for path in FULL_AUDIO_DIR.glob(f"*{EXTENDED_MARKER}*.mp3"):
        path.unlink(missing_ok=True)
    for path in FULL_AUDIO_DIR.glob(f"*{CLIPS_MARKER}*.mp3"):
        path.unlink(missing_ok=True)


def _plus_custom_path(mode: str) -> Path:
    stem = Path(COURSE_FILES[mode]).stem
    return FULL_AUDIO_DIR / f"{stem}{PLUS_CUSTOM_MARKER}.mp3"


def plus_custom_course_path(mode: str) -> Path | None:
    p = _plus_custom_path(mode)
    if p.exists() and p.stat().st_size > 1000:
        return p
    return None


def official_course_path(mode: str) -> Path | None:
    base = FULL_AUDIO_DIR / COURSE_FILES[mode]
    if base.exists() and base.stat().st_size > 1000:
        return base
    return None


def _base_for_append(mode: str) -> Path | None:
    """Best existing MP3 to append new word clips onto."""
    if plus := plus_custom_course_path(mode):
        return plus
    if official := official_course_path(mode):
        return official
    clips = FULL_AUDIO_DIR / f"{Path(COURSE_FILES[mode]).stem}{CLIPS_MARKER}_{_vocab_signature()}.mp3"
    if clips.exists() and clips.stat().st_size > 1000:
        return clips
    return None


def _base_for_rebuild(mode: str) -> Path | None:
    """Official or clip-built base — excludes existing plus_custom file."""
    if official := official_course_path(mode):
        return official
    clips = FULL_AUDIO_DIR / f"{Path(COURSE_FILES[mode]).stem}{CLIPS_MARKER}_{_vocab_signature()}.mp3"
    if clips.exists() and clips.stat().st_size > 1000:
        return clips
    return None


def ensure_custom_word_clips(word: Word) -> list[str]:
    """Generate course-voice clips (Katja/Jenny) matching the full MP3 builder."""
    return ensure_course_clips(word)


def rebuild_plus_custom_courses(
    progress: Callable[[str], None] | None = None,
) -> tuple[list[str], list[str], int, int]:
    """
    Generate missing pronunciation clips for custom cards and rebuild plus_custom MP3s.
    Returns (modes updated, errors, in_both count, in_de_only count).
    """

    def _log(msg: str) -> None:
        if progress:
            progress(msg)

    custom = load_custom_vocabulary("a1")
    if not custom:
        return [], [], 0, 0

    ffmpeg = _ffmpeg()
    if not ffmpeg:
        return [], ["Install ffmpeg to merge MP3 courses (`brew install ffmpeg` or `pip install imageio-ffmpeg`)."], 0, 0

    errors: list[str] = []
    for i, word in enumerate(custom, start=1):
        _log(f"Voice clip {i}/{len(custom)}: {word.german}")
        errors.extend(ensure_custom_word_clips(word))

    in_de_only = sum(1 for w in custom if get_course_clip_path(w.id, "de"))
    in_both = sum(
        1
        for w in custom
        if get_course_clip_path(w.id, "de") and get_course_clip_path(w.id, "en")
    )

    if in_de_only == 0:
        if not errors:
            errors.append("No pronunciation clips could be created for your custom cards.")
        return [], errors, in_both, in_de_only

    ok_modes: list[str] = []
    FULL_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="a1_rebuild_") as tmp_name:
        tmp = Path(tmp_name)
        for mode in COURSE_FILES:
            label = MODE_LABELS[mode]
            _log(f"Merging {label}…")
            segments: list[Path] = []
            for word in custom:
                segments.extend(_word_segments(word, mode, tmp, ffmpeg))
            if not segments:
                errors.append(f"{label}: no clips with required audio.")
                continue

            base = _base_for_rebuild(mode)
            parts: list[Path] = []
            if base:
                parts.append(base)
            parts.extend(segments)
            out = _plus_custom_path(mode)
            if _concat_mp3(parts, out, ffmpeg):
                ok_modes.append(mode)
                _log(f"Saved {out.name}")
            else:
                errors.append(f"{label}: merge failed.")

    return ok_modes, errors, in_both, in_de_only


def append_word_to_courses(word: Word, *, generate_missing: bool = False) -> tuple[list[str], list[str]]:
    """
    Append one card's saved clips to the course MP3 files.
    Returns (modes updated, error messages).
    """
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        return [], ["Install ffmpeg to update MP3 courses (`brew install ffmpeg`)."]

    errors: list[str] = []
    errors.extend(ensure_custom_word_clips(word))

    ok_modes: list[str] = []
    FULL_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="a1_append_") as tmp_name:
        tmp = Path(tmp_name)
        for mode in COURSE_FILES:
            segments = _word_segments(word, mode, tmp, ffmpeg)
            if not segments:
                label = MODE_LABELS[mode]
                if mode == "de_only":
                    errors.append(f"{label}: save German audio first.")
                else:
                    errors.append(f"{label}: save German and English audio.")
                continue

            base = _base_for_append(mode)
            parts: list[Path] = []
            if base:
                parts.append(base)
            parts.extend(segments)
            out = _plus_custom_path(mode)
            if _concat_mp3(parts, out, ffmpeg):
                ok_modes.append(mode)
            else:
                errors.append(f"{MODE_LABELS[mode]}: merge failed.")

    return ok_modes, errors


def _ensure_silence(seconds: float, cache_dir: Path, ffmpeg: str, label: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    name = f"pause_{label}_{seconds:.1f}s.mp3"
    path = cache_dir / name
    if path.exists() and path.stat().st_size > 100:
        return path
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=24000:cl=mono",
            "-t",
            str(seconds),
            "-q:a",
            "9",
            "-acodec",
            "libmp3lame",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


def _to_mp3(src: Path, dest: Path, ffmpeg: str) -> Path | None:
    if not src.exists() or src.stat().st_size < 200:
        return None
    if src.suffix.lower() == ".mp3":
        return src
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [ffmpeg, "-y", "-i", str(src), "-c:a", "libmp3lame", "-q:a", "4", str(dest)],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        return None
    return dest if dest.exists() and dest.stat().st_size > 200 else None


def _word_segments(word: Word, mode: str, tmp: Path, ffmpeg: str) -> list[Path]:
    de_src = get_course_clip_path(word.id, "de") or user_recorded_clip(word.id, "de")
    en_src = get_course_clip_path(word.id, "en") or user_recorded_clip(word.id, "en")
    if not de_src:
        return []

    de_mp3 = de_src if de_src.suffix.lower() == ".mp3" else _to_mp3(de_src, tmp / f"{word.id:04d}_de.mp3", ffmpeg)
    if not de_mp3:
        return []

    cache = FULL_AUDIO_DIR / ".course_cache"
    pause_after = _ensure_silence(PAUSE_AFTER_WORD_SEC, cache, ffmpeg, "after")

    if mode == "de_only":
        return [de_mp3, pause_after]

    if not en_src:
        return []
    en_mp3 = en_src if en_src.suffix.lower() == ".mp3" else _to_mp3(en_src, tmp / f"{word.id:04d}_en.mp3", ffmpeg)
    if not en_mp3:
        return []

    pause_mid = _ensure_silence(PAUSE_DE_BEFORE_EN_SEC, cache, ffmpeg, "mid")
    if mode == "de_en":
        return [de_mp3, pause_mid, en_mp3, pause_after]
    return [en_mp3, pause_mid, de_mp3, pause_after]


def _concat_mp3(parts: list[Path], out: Path, ffmpeg: str) -> bool:
    existing = [p for p in parts if p.exists() and p.stat().st_size > 200]
    if not existing:
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        list_file = Path(f.name)
        for part in existing:
            escaped = str(part.resolve()).replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
    try:
        for reencode in (False, True):
            cmd = [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
            ]
            if reencode:
                cmd.extend(["-c:a", "libmp3lame", "-q:a", "4", str(out)])
            else:
                cmd.extend(["-c", "copy", str(out)])
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError:
                continue
            if out.exists() and out.stat().st_size > 1000:
                return True
        return False
    finally:
        list_file.unlink(missing_ok=True)


def _clips_course_path(mode: str) -> Path:
    stem = Path(COURSE_FILES[mode]).stem
    return FULL_AUDIO_DIR / f"{stem}{CLIPS_MARKER}_{_vocab_signature()}.mp3"


def count_clip_words(mode: str, words: list[Word] | None = None) -> int:
    words = words or load_all_vocabulary("a1")
    if mode == "de_only":
        return sum(1 for w in words if get_word_audio_path(w.id, "de"))
    return sum(
        1
        for w in words
        if get_word_audio_path(w.id, "de") and get_word_audio_path(w.id, "en")
    )


def build_course_from_clips(mode: str, words: list[Word] | None = None) -> Path | None:
    """Merge per-word clips into a course MP3 (cached)."""
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        return None

    words = words or load_all_vocabulary("a1")
    out = _clips_course_path(mode)
    if out.exists() and out.stat().st_size > 1000:
        return out

    parts: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="a1_course_") as tmp_name:
        tmp = Path(tmp_name)
        for word in words:
            parts.extend(_word_segments(word, mode, tmp, ffmpeg))

    word_count = count_clip_words(mode, words)
    if word_count == 0 or not parts:
        return None

    if _concat_mp3(parts, out, ffmpeg):
        return out
    return None


def build_extended_course(mode: str) -> Path | None:
    """Append custom-card clips to an existing base or clip-built course."""
    custom = load_custom_vocabulary("a1")
    if not custom:
        return None

    ffmpeg = _ffmpeg()
    if not ffmpeg:
        return None

    base = FULL_AUDIO_DIR / COURSE_FILES[mode]
    if base.exists() and base.stat().st_size > 1000:
        base_part: Path | None = base
    else:
        base_part = build_course_from_clips(mode)

    out = FULL_AUDIO_DIR / (
        f"{Path(COURSE_FILES[mode]).stem}{EXTENDED_MARKER}_{_custom_signature()}.mp3"
    )
    if out.exists() and out.stat().st_size > 1000:
        return out

    parts: list[Path] = []
    if base_part:
        parts.append(base_part)

    with tempfile.TemporaryDirectory(prefix="a1_course_ext_") as tmp_name:
        tmp = Path(tmp_name)
        for word in custom:
            parts.extend(_word_segments(word, mode, tmp, ffmpeg))

    if len(parts) <= (1 if base_part else 0):
        return base_part

    if _concat_mp3(parts, out, ffmpeg):
        return out
    return base_part


def course_audio_path(mode: str) -> tuple[Path | None, bool, str]:
    """
    Return (path, includes_custom_cards, source).
    source is one of: plus_custom, official, clips, extended, missing
    """
    if plus := plus_custom_course_path(mode):
        return plus, True, "plus_custom"

    custom = load_custom_vocabulary("a1")

    official = official_course_path(mode)
    if official and custom:
        extended = build_extended_course(mode)
        if extended and EXTENDED_MARKER in extended.name:
            return extended, True, "extended"
        return official, False, "official"

    if official:
        return official, False, "official"

    clips = build_course_from_clips(mode)
    if clips:
        return clips, bool(custom), "clips"

    if custom:
        extended = build_extended_course(mode)
        if extended:
            return extended, True, "extended"

    return None, False, "missing"


def extended_course_status() -> tuple[int, int, int, list[str]]:
    """Return (custom count, in DE+EN courses, in DE-only course, skipped labels)."""
    custom = load_custom_vocabulary("a1")
    in_both = 0
    in_de_only = 0
    skipped: list[str] = []
    for word in custom:
        de = get_course_clip_path(word.id, "de")
        en = get_course_clip_path(word.id, "en")
        if de:
            in_de_only += 1
        if de and en:
            in_both += 1
        elif de:
            skipped.append(f"{word.german} (add English audio for full courses)")
        else:
            skipped.append(f"{word.german} (no saved audio)")
    return len(custom), in_both, in_de_only, skipped


def ffmpeg_available() -> bool:
    return _ffmpeg() is not None


def courses_missing() -> bool:
    return all(official_course_path(m) is None for m in COURSE_FILES)


def clip_words_available(mode: str = "de_en") -> int:
    return count_clip_words(mode)
