from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from urllib.parse import quote

import requests

from a1.config import (
    AUDIO_DIR,
    FULL_AUDIO_DIR,
    PAUSE_AFTER_WORD_SEC,
    PAUSE_DE_BEFORE_EN_SEC,
    RATE_DE,
    RATE_EN,
    VOICE_DE,
    VOICE_EN,
)
from a1.articles import german_with_article
from a1.vocab import english_short  # noqa: F401 — used by callers

MACOS_VOICE_DE = "Anna"
MACOS_VOICE_EN = "Samantha"
MACOS_RATE_DE = 120
MACOS_RATE_EN = 175

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

_HTTP = requests.Session()
_HTTP.trust_env = False
_HTTP.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class AudioGenerationError(RuntimeError):
    """Raised when word audio cannot be generated."""


def _path(word_id: int, kind: str) -> Path:
    return AUDIO_DIR / f"{word_id:04d}_{kind}.mp3"


def _mp3_valid(data: bytes) -> bool:
    if len(data) < 600:
        return False
    return data[:3] == b"ID3" or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)


def _audio_valid(path: Path) -> bool:
    if not path.exists():
        return False
    if path.stat().st_size < 600:
        return False
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wf:
                return wf.getnframes() > 0
        except Exception:
            return False
    if path.suffix.lower() == ".mp3":
        return _mp3_valid(path.read_bytes()[:4])
    return True


def _resolve_cached(path: Path) -> Path | None:
    for candidate in (path, path.with_suffix(".wav")):
        if _audio_valid(candidate):
            return candidate
        if candidate.exists():
            candidate.unlink(missing_ok=True)
    return None


def full_course_mp3(name: str) -> Path | None:
    p = FULL_AUDIO_DIR / name
    return p if p.exists() else None


def _macos_tts_available() -> bool:
    return sys.platform == "darwin" and shutil.which("say") and shutil.which("afconvert")


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


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in _PROXY_KEYS:
        env.pop(key, None)
    return env


def _tts_macos(text: str, voice: str, rate: int, out_mp3: Path) -> Path:
    """Offline fallback using macOS say + afconvert (returns .wav path)."""
    if not _macos_tts_available():
        raise AudioGenerationError("Offline TTS is unavailable on this system.")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out_wav = out_mp3.with_suffix(".wav")
    out_wav.unlink(missing_ok=True)
    env = _subprocess_env()
    errors: list[str] = []

    attempts: list[list[str]] = [
        ["say", "-v", voice, "-o", "{out}", text],
        ["say", "-v", voice, "-r", str(rate), "-o", "{out}", text],
        ["say", "-v", voice, "-o", "{out}", "--file-format=WAVE", text],
        ["say", "-v", voice, "-o", "{out}", "--file-format=AIFF", text],
    ]

    for template in attempts:
        aiff = out_mp3.with_suffix(".aiff")
        m4a = out_mp3.with_suffix(".m4a")
        aiff.unlink(missing_ok=True)
        m4a.unlink(missing_ok=True)
        out_target = out_wav if "--file-format=WAVE" in template else aiff
        try:
            cmd = [
                part.format(out=str(out_target)) if "{out}" in part else part for part in template
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
            if out_target.exists() and out_target.stat().st_size > 600:
                if out_target == out_wav:
                    if _audio_valid(out_wav):
                        return out_wav
                else:
                    subprocess.run(
                        ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", str(aiff), str(out_wav)],
                        check=True,
                        capture_output=True,
                        text=True,
                        env=env,
                    )
                    if _audio_valid(out_wav):
                        return out_wav
            out_wav.unlink(missing_ok=True)

            cmd_m4a = ["say", "-v", voice, "-o", str(m4a), "--data-format=aac", text]
            subprocess.run(cmd_m4a, check=True, capture_output=True, text=True, env=env)
            if m4a.exists() and m4a.stat().st_size > 600:
                subprocess.run(
                    ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", str(m4a), str(out_wav)],
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env,
                )
                if _audio_valid(out_wav):
                    return out_wav
            out_wav.unlink(missing_ok=True)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            if detail:
                errors.append(detail)
        finally:
            aiff.unlink(missing_ok=True)
            m4a.unlink(missing_ok=True)

    raise AudioGenerationError(
        "Mac built-in voice failed. Open System Settings → Accessibility → Spoken Content, "
        "then test in Terminal: say -v Anna \"hello\""
        + (f" ({errors[-1]})" if errors else "")
    )


def _tts_google(text: str, lang: str, out: Path) -> Path:
    url = (
        "https://translate.google.com/translate_tts"
        f"?ie=UTF-8&client=tw-ob&q={quote(text)}&tl={lang}"
    )
    try:
        with _without_proxy_env():
            response = _HTTP.get(url, timeout=20)
    except Exception as exc:
        raise AudioGenerationError("Google Translate speech is unreachable.") from exc
    if response.status_code != 200 or not _mp3_valid(response.content):
        raise AudioGenerationError("Google Translate speech failed.")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out.write_bytes(response.content)
    return out


async def _tts_edge(text: str, voice: str, rate: str, out: Path) -> None:
    import edge_tts

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    await asyncio.wait_for(
        edge_tts.Communicate(text, voice, rate=rate).save(str(out)),
        timeout=12,
    )


def _run_async(coro) -> None:
    try:
        asyncio.run(coro)
    except RuntimeError as exc:
        msg = str(exc).lower()
        if "asyncio.run()" in msg or "event loop" in msg:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(coro)
            finally:
                loop.close()
        else:
            raise


def _tts_edge_sync(text: str, voice: str, rate: str, out: Path) -> Path:
    out.unlink(missing_ok=True)

    async def run() -> None:
        await _tts_edge(text, voice, rate, out)

    try:
        with _without_proxy_env():
            _run_async(run())
    except TimeoutError as exc:
        out.unlink(missing_ok=True)
        raise AudioGenerationError("Microsoft speech service timed out.") from exc
    except Exception as exc:
        out.unlink(missing_ok=True)
        raise AudioGenerationError(
            "Could not reach Microsoft speech service (edge-tts). "
            "Check your internet connection and try again."
        ) from exc

    if not _audio_valid(out):
        out.unlink(missing_ok=True)
        raise AudioGenerationError("Online TTS produced an empty audio file.")
    return out


def _generate_clip(text: str, voice: str, rate: str, out: Path) -> Path:
    """Generate one clip using offline Mac voice, then online fallbacks."""
    errors: list[str] = []
    lang = "de" if voice.startswith("de-") else "en"

    if _macos_tts_available():
        mac_voice = MACOS_VOICE_DE if lang == "de" else MACOS_VOICE_EN
        mac_rate = MACOS_RATE_DE if lang == "de" else MACOS_RATE_EN
        try:
            return _tts_macos(text, mac_voice, mac_rate, out)
        except AudioGenerationError as exc:
            errors.append(str(exc))

    try:
        return _tts_google(text, lang, out)
    except AudioGenerationError as exc:
        errors.append(str(exc))

    try:
        return _tts_edge_sync(text, voice, rate, out)
    except AudioGenerationError as exc:
        errors.append(str(exc))

    hint = (
        "Use **Preview web voice** or record your own clip in the app, "
        "or run `python scripts/pregenerate_word_audio.py` while online."
    )
    raise AudioGenerationError(f"All server speech methods failed. {hint}")


def _course_clip_dir() -> Path:
    return AUDIO_DIR / "course"


def course_clip_path(word_id: int, kind: str) -> Path:
    """Path for course-voice clip (Katja/Jenny), used when merging into full MP3s."""
    return _course_clip_dir() / f"{word_id:04d}_{kind}.mp3"


def get_course_clip_path(word_id: int, kind: str) -> Path | None:
    for ext in (".mp3", ".wav"):
        path = _course_clip_dir() / f"{word_id:04d}_{kind}{ext}"
        if _audio_valid(path):
            return path
    return None


def user_recorded_clip(word_id: int, kind: str) -> Path | None:
    """Saved clip from Add card / Manage cards (not course-voice cache)."""
    base = AUDIO_DIR / f"{word_id:04d}_{kind}"
    for ext in _AUDIO_EXTS:
        path = base.with_suffix(ext)
        if _audio_valid(path):
            return path
    return None


def _ffmpeg_exe() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _import_clip_to_course(src: Path, word_id: int, kind: str) -> Path | None:
    dest = course_clip_path(word_id, kind)
    _course_clip_dir().mkdir(parents=True, exist_ok=True)
    dest.unlink(missing_ok=True)
    if src.suffix.lower() == ".mp3" and _audio_valid(src):
        shutil.copy2(src, dest)
        return dest if _audio_valid(dest) else None
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        return None
    try:
        subprocess.run(
            [ffmpeg, "-y", "-i", str(src), "-c:a", "libmp3lame", "-q:a", "4", str(dest)],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        return None
    return dest if dest.exists() and dest.stat().st_size > 200 else None


def clear_course_clips(word_id: int) -> None:
    """Remove cached course-voice clips for one word."""
    for kind in ("de", "en"):
        for ext in (".mp3", ".wav"):
            path = _course_clip_dir() / f"{word_id:04d}_{kind}{ext}"
            path.unlink(missing_ok=True)


def _generate_course_clip(text: str, voice: str, rate: str, out: Path) -> Path:
    """Course MP3 clip — Mac voice offline, Katja/Jenny online (same chain as flashcard TTS)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    for ext in (".mp3", ".wav"):
        out.with_suffix(ext).unlink(missing_ok=True)
    return _generate_clip(text, voice, rate, out.with_suffix(".mp3"))


def ensure_course_clips(word) -> list[str]:
    """Generate DE/EN course clips for one word. Returns error messages."""
    from a1.articles import german_de_speech
    from a1.vocab import english_short

    _course_clip_dir().mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    specs = (
        ("de", german_de_speech(word), VOICE_DE, RATE_DE),
        ("en", english_short(word.english), VOICE_EN, RATE_EN),
    )
    missing_kinds: list[str] = []
    for kind, text, voice, rate in specs:
        if get_course_clip_path(word.id, kind):
            continue
        if not text.strip():
            missing_kinds.append(kind)
            continue
        try:
            _generate_course_clip(text, voice, rate, course_clip_path(word.id, kind))
        except AudioGenerationError:
            if user := user_recorded_clip(word.id, kind):
                if not _import_clip_to_course(user, word.id, kind):
                    missing_kinds.append(kind)
            else:
                missing_kinds.append(kind)

    if missing_kinds:
        if "de" in missing_kinds and "en" in missing_kinds:
            errors.append(
                f"{word.german}: could not create German or English audio "
                "(connect to internet, or record clips on Add card)."
            )
        elif "de" in missing_kinds:
            errors.append(f"{word.german}: missing German audio.")
        else:
            errors.append(f"{word.german}: missing English audio.")
    return errors


def ensure_audio_sync(
    word_id: int,
    german: str,
    english: str,
    *,
    article: str = "",
    section: str = "",
) -> tuple[Path, Path, Path]:
    """Return paths to cached de / en_meaning clips (generate if missing)."""
    en = english_short(english)
    de_text = german_with_article(german, section=section, article=article)
    p_de = _path(word_id, "de")
    p_en = _path(word_id, "en")
    cached_de = _resolve_cached(p_de)
    cached_en = _resolve_cached(p_en)

    if not cached_de:
        cached_de = _generate_clip(de_text, VOICE_DE, RATE_DE, p_de)
    if not cached_en:
        cached_en = _generate_clip(en, VOICE_EN, RATE_EN, p_en)

    return cached_de, cached_en, cached_de


_AUDIO_EXTS = (".mp3", ".wav", ".webm", ".ogg", ".m4a")


def ext_from_mime(mime: str) -> str:
    mime = (mime or "").lower()
    if "mpeg" in mime or "mp3" in mime:
        return ".mp3"
    if "wav" in mime:
        return ".wav"
    if "ogg" in mime:
        return ".ogg"
    if "mp4" in mime or "m4a" in mime:
        return ".m4a"
    return ".webm"


def get_word_audio_path(word_id: int, kind: str) -> Path | None:
    """Return saved audio file for a word clip, if any."""
    base = AUDIO_DIR / f"{word_id:04d}_{kind}"
    for ext in _AUDIO_EXTS:
        path = base.with_suffix(ext)
        if not path.exists() or path.stat().st_size < 200:
            continue
        if ext == ".wav" and not _audio_valid(path):
            continue
        if ext == ".mp3" and not _mp3_valid(path.read_bytes()[:4]):
            continue
        return path
    course = get_course_clip_path(word_id, kind)
    if course:
        return course
    return _resolve_cached(_path(word_id, kind))


def save_word_audio(word_id: int, kind: str, data: bytes, ext: str = ".webm") -> Path:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    if ext not in _AUDIO_EXTS:
        ext = ".webm"
    for old in AUDIO_DIR.glob(f"{word_id:04d}_{kind}.*"):
        old.unlink(missing_ok=True)
    path = AUDIO_DIR / f"{word_id:04d}_{kind}{ext}"
    path.write_bytes(data)
    return path


def delete_word_audio(word_id: int, kind: str | None = None) -> None:
    """Remove saved pronunciation clips for a word."""
    pattern = f"{word_id:04d}_{kind}.*" if kind else f"{word_id:04d}_*"
    for path in AUDIO_DIR.glob(pattern):
        path.unlink(missing_ok=True)


def fetch_online_audio(text: str, lang: str) -> tuple[bytes, str]:
    """Try to fetch pronunciation audio online (returns bytes + extension)."""
    text = text.strip()
    if not text:
        raise AudioGenerationError("Enter the word first.")
    voice = VOICE_DE if lang == "de" else VOICE_EN
    rate = RATE_DE if lang == "de" else RATE_EN
    tmp = AUDIO_DIR / f"_fetch_{lang}.mp3"
    tmp.unlink(missing_ok=True)
    try:
        path = _generate_clip(text, voice, rate, tmp)
        ext = path.suffix or ".mp3"
        data = path.read_bytes()
        if len(data) < 200:
            raise AudioGenerationError("Online audio was empty.")
        return data, ext
    finally:
        tmp.unlink(missing_ok=True)
        for p in AUDIO_DIR.glob(f"_fetch_{lang}.*"):
            p.unlink(missing_ok=True)
