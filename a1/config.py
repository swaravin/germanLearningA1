from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ASSETS_DIR = ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
AUDIO_DIR = ASSETS_DIR / "audio"
FULL_AUDIO_DIR = ASSETS_DIR / "full"
CUSTOM_SECTION = "My cards"

# CEFR word lists live under data/levels/<id>/ — see a1.levels
LEVELS_MANIFEST = DATA_DIR / "levels.json"
LEVELS_DIR = DATA_DIR / "levels"

VOICE_DE = "de-DE-KatjaNeural"
VOICE_EN = "en-US-JennyNeural"
RATE_DE = "-32%"
RATE_EN = "+0%"
PAUSE_AFTER_WORD_SEC = 1.0
PAUSE_DE_BEFORE_EN_SEC = 0.9
