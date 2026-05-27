# German A1 — Learn App

Flashcard app for **~450 German A1 words** plus your own custom cards. Study with images, slow German pronunciation, English meanings, example sentences (**der/die/das** on nouns), and full listen-along MP3 courses.

**Repository:** [github.com/swaravin/germanLearningA1](https://github.com/swaravin/germanLearningA1)

---

## Features

| Mode | What it does |
|------|----------------|
| **Flashcards** | Picture, German (with article), flip for English, play audio |
| **Browse list** | Search the full vocabulary + your custom cards |
| **Add card** | Create cards, record/find pronunciation, append to course MP3s |
| **Manage cards** | Edit or delete custom cards |
| **Listen** | Full German→English, English→German, and German-only MP3 courses |
| **iPhone PWA** | Offline flashcards — install from Safari (see below) |

Custom cards are saved locally in `data/custom_vocabulary.json` and can be merged into the long MP3 files at the end of each course.

---

## Quick start (Mac / desktop)

```bash
git clone https://github.com/swaravin/germanLearningA1.git
cd germanLearningA1

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional: regenerate vocabulary export from source docx
python scripts/export_vocabulary.py

streamlit run app.py
```

Open the URL in the terminal (usually **http://localhost:8501**).

> Use the project venv (`.venv/bin/streamlit run app.py`). System Python may miss packages like `edge-tts`.

---

## Install on iPhone

### Option A — Offline flashcards (home-screen app)

Works without a server after the first visit.

```bash
python scripts/build_mobile_pwa.py   # sync vocabulary into mobile/data/
python3 -m http.server 8080 --directory mobile
```

On your iPhone (same Wi‑Fi as your Mac):

1. Safari → `http://<your-mac-ip>:8080`
2. **Share** → **Add to Home Screen**

Or host the `mobile/` folder on **GitHub Pages** (recommended — always on, no Mac needed):

1. Repo **Settings → Pages → Build and deployment → Source:** choose **GitHub Actions** (not “Deploy from branch”).
2. Push to `main` — the workflow `.github/workflows/pages.yml` builds and deploys automatically.
3. Your app URL: **https://swaravin.github.io/germanLearningA1/**
4. iPhone Safari → that URL → **Share → Add to Home Screen**

Or use Netlify / Cloudflare Pages with the `mobile/` folder as the publish directory.

### Option B — Full app (add cards, MP3 tools)

Deploy to [Streamlit Community Cloud](https://streamlit.io/cloud):

1. Connect this GitHub repo
2. Main file: `app.py`
3. On iPhone: open your `*.streamlit.app` URL → **Share → Add to Home Screen**

### Option C — Listen on the go

Copy the MP3s from `assets/full/` to your iPhone (**AirDrop** or **Files**), then play in Music or VLC:

- `German_A1_Audio_German_and_English_plus_custom.mp3`
- `German_A1_Audio_English_and_German_plus_custom.mp3`
- `German_A1_Audio_German_only_plus_custom.mp3`

---

## Full course MP3s

Pre-built MP3s are included under `assets/full/`. To rebuild (needs **internet**, ~15–30 min):

```bash
pip install imageio-ffmpeg   # or: brew install ffmpeg
python scripts/build_german_vocab_learn_pack.py --audio-only
```

**Voices:** German — Katja (`de-DE-KatjaNeural`, slow); English — Jenny (`en-US-JennyNeural`).

**Custom cards:** On **Listen**, click **Generate pronunciation & add custom cards to MP3s**. Offline uses Mac voice; online uses Katja/Jenny. Pauses match the main course (1.0 s between items, 0.9 s between German and English).

---

## Project layout

```
app.py                 Streamlit UI
a1/                    Vocabulary, audio, images, articles, full-course merge
data/
  vocabulary.json      Built-in ~450 words
  custom_vocabulary.json   Your cards (created at runtime)
assets/
  audio/               Per-word clips (generated locally, gitignored)
  full/                Full course MP3s + Word docs
mobile/                iPhone PWA (offline flashcards)
scripts/               Export vocab, build MP3s, mobile sync
```

---

## Requirements

- Python 3.10+
- **ffmpeg** for merging MP3s: `brew install ffmpeg` or `pip install imageio-ffmpeg`
- Internet for: image fetch, online TTS, edge-tts course rebuild
- Mac **say** voice works offline for custom-card clips

---

## Regenerate content

```bash
python scripts/export_vocabulary.py
python scripts/build_german_vocab_learn_pack.py      # MP3s + docx
python scripts/build_german_vocab_doc.py             # vocabulary Word doc
python scripts/build_mobile_pwa.py                   # sync data for iPhone PWA
python scripts/apply_articles.py                     # patch articles in JSON
```

---

## License

Personal learning project. Vocabulary and audio are for private study.
