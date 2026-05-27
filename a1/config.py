from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ASSETS_DIR = ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
AUDIO_DIR = ASSETS_DIR / "audio"
FULL_AUDIO_DIR = ASSETS_DIR / "full"
VOCAB_JSON = DATA_DIR / "vocabulary.json"
CUSTOM_VOCAB_JSON = DATA_DIR / "custom_vocabulary.json"
CUSTOM_SECTION = "My cards"

VOICE_DE = "de-DE-KatjaNeural"
VOICE_EN = "en-US-JennyNeural"
RATE_DE = "-32%"
RATE_EN = "+0%"
# Match scripts/build_german_vocab_learn_pack.py pauses between vocabulary items
PAUSE_AFTER_WORD_SEC = 1.0
PAUSE_DE_BEFORE_EN_SEC = 0.9
