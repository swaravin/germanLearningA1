#!/usr/bin/env python3
"""Import Leben in Deutschland PDF → questions.json + vocabulary cards."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/A1/gesamtfragenkatalog-lebenindeutschland.pdf"
FALLBACK_PDF = ROOT / "data" / "lid" / "gesamtfragenkatalog-lebenindeutschland.pdf"
ANSWERS_SOURCE = ROOT / "data" / "lid_questions_source.json"
OUT_DIR = ROOT / "data" / "lid"
QUESTIONS_JSON = OUT_DIR / "questions.json"
VOCAB_OUT = ROOT / "data" / "levels" / "a1" / "lid_vocabulary.json"
SECTION_LID_PREFIX = "17. Leben in Deutschland"  # legacy question cards — removed on import
SECTION_WORDS = "18. Leben deutsch words"
WORDS_START_ID = 1400

STOPWORDS = frozenset(
    """
    der die das den dem des ein eine einen einem einer eines
    und oder aber wenn weil dass das ist sind war waren wird
    nicht nur auch schon noch sehr hier dort dann wenn als
    bei von zu mit nach aus für auf über unter vor hinter
    ich du er sie es wir ihr sie Sie man
    in an am im zum zur vom vom beim
    alle jeder jede jedes kein keine
    was wer wie welche welches welcher wann wo warum
    jahre jahr monat tag jahren
    staat regierung kirchen kreis gemeinde alter kinder
    """.split()
)

GENERIC_SKIP = frozenset(
    """
    deutschland jahren staat regierung kirchen kreis gemeinde alter kinder
    land tag rat amt zentrale verbraucher bildung arbeit frau mann
    """.split()
)

SKIP_PHRASE_RE = re.compile(
    r"^(Bild \d|Ja,|Nein,|Man darf|Die |Der |Das |In |Es |Wer |Was |Wie |Welche|Welches|Welcher|Ab |Für )",
    re.I,
)

MAX_VOCAB_WORDS = 3

SENTENCE_START_RE = re.compile(
    r"^(alle|jeder|jede|jedes|er |sie |man |ich |wir |ihr |es |wenn |durch |von |kann |"
    r"sie müssen|er baut|er bezahlt|er produziert|er verkauft|er fördert|ich lasse|"
    r"jeder kann|alle menschen|alle sollen|alle sind|bürger )",
    re.I,
)

VERB_WORDS = frozenset(
    "sind ist sind war waren wird werden habe hat haben hatte hatten darf dürfen muss müssen "
    "kann können soll sollen glauben demonstrieren anmelden kämpft verlieren bestraft "
    "bezahlt baut produziert verkauft fördert lasse teilnimmt gilt wählt auswählt".split()
)

OPTION_PREFIX = re.compile(r"^[\uf0a3□☐▪•\-]\s*")
STATE_LINE = re.compile(
    r"Frag(?:en)?\s+für\s+das\s+Bundesland\s+(.+?)\s*$",
    re.IGNORECASE,
)
BUNDESLAENDER = {
    "Baden-Württemberg",
    "Bayern",
    "Berlin",
    "Brandenburg",
    "Bremen",
    "Hamburg",
    "Hessen",
    "Mecklenburg-Vorpommern",
    "Niedersachsen",
    "Nordrhein-Westfalen",
    "Rheinland-Pfalz",
    "Saarland",
    "Sachsen",
    "Sachsen-Anhalt",
    "Schleswig-Holstein",
    "Thüringen",
}

BUNDESLAND_EN = {
    "Baden-Württemberg": "Baden-Württemberg",
    "Bayern": "Bavaria",
    "Berlin": "Berlin",
    "Brandenburg": "Brandenburg",
    "Bremen": "Bremen",
    "Hamburg": "Hamburg",
    "Hessen": "Hesse",
    "Mecklenburg-Vorpommern": "Mecklenburg-Western Pomerania",
    "Niedersachsen": "Lower Saxony",
    "Nordrhein-Westfalen": "North Rhine-Westphalia",
    "Rheinland-Pfalz": "Rhineland-Palatinate",
    "Saarland": "Saarland",
    "Sachsen": "Saxony",
    "Sachsen-Anhalt": "Saxony-Anhalt",
    "Schleswig-Holstein": "Schleswig-Holstein",
    "Thüringen": "Thuringia",
}

LID_GLOSSARY: dict[str, str] = {
    **BUNDESLAND_EN,
    "Meinungsfreiheit": "freedom of expression",
    "Religionsfreiheit": "freedom of religion",
    "Pressefreiheit": "freedom of the press",
    "Versammlungsfreiheit": "freedom of assembly",
    "Wahlrecht": "right to vote",
    "Wahlgeheimnis": "secret ballot",
    "Grundgesetz": "Basic Law (constitution)",
    "Bundesrepublik Deutschland": "Federal Republic of Germany",
    "Bundestag": "German federal parliament",
    "Bundesrat": "Federal Council",
    "Bundeskanzler": "Federal Chancellor",
    "Bundespräsident": "Federal President",
    "Bundesverfassungsgericht": "Federal Constitutional Court",
    "Rechtsstaat": "constitutional state / rule of law",
    "Demokratie": "democracy",
    "Diktatur": "dictatorship",
    "Monarchie": "monarchy",
    "Gewaltenteilung": "separation of powers",
    "Menschenwürde": "human dignity",
    "Gleichberechtigung": "equal rights",
    "Steuern": "taxes",
    "Sozialversicherung": "social insurance",
    "Kindergeld": "child benefit",
    "Geschichtsunterricht": "history lessons",
    "Religionsunterricht": "religious education",
    "Politikunterricht": "politics lessons",
    "Sprachunterricht": "language classes",
    "schwarz-rot-gold": "black-red-gold",
    "schwarz-gelb": "black-yellow",
    "schwarz-rot": "black-red",
    "weiß-rot": "white-red",
    "blau-weiß-rot": "blue-white-red",
    "grün-weiß-rot": "green-white-red",
    "rot-weiß": "red-white",
    "München": "Munich",
    "Polen": "Poland",
    "Tschechien": "Czech Republic",
    "Frankreich": "France",
    "Österreich": "Austria",
    "Schweiz": "Switzerland",
    "Dänemark": "Denmark",
    "Niederlande": "Netherlands",
    "Luxemburg": "Luxembourg",
    "Belgien": "Belgium",
    "Frieden": "peace",
    "Sicherheit": "security",
    "Stimme": "vote",
    "Briefwahl": "postal vote",
    "Judikative": "judiciary",
    "Legislative": "legislature",
    "Exekutive": "executive",
    "Ordnungsamt": "public order office",
    "Verbraucherzentrale": "consumer advice centre",
    "Direktive": "directive (EU law)",
    "Portugal": "Portugal",
    "Griechenland": "Greece",
    "Bulgarien": "Bulgaria",
    "weiß-blau": "white-blue",
    "schwarz-gold": "black-gold",
    "Gesetz": "law",
    "Gleichheit": "equality",
    "Verfassung": "constitution",
    "Demonstration": "demonstration",
    "Freiheit": "freedom",
    "Einigkeit": "unity",
    "Recht": "justice / law",
    "Behörde": "authority / public office",
    "Gaststättenerlaubnis": "restaurant licence",
    "Volksaufstand": "popular uprising",
    "Streik": "strike",
    "Kapitulation": "surrender",
    "Nationalsozialismus": "National Socialism",
    "Rentenversicherung": "pension insurance",
    "Krankenversicherung": "health insurance",
    "SPD": "Social Democratic Party (SPD)",
    "Abgeordnete": "member of parliament",
    "Minister": "minister",
    "Kündigung": "dismissal / termination",
    "Kündigungsfrist": "notice period",
    "Kündigungsschutzklage": "wrongful dismissal lawsuit",
    "Arbeitsgericht": "labour court",
}


@dataclass
class ParsedQuestion:
    part: str  # "general" | state slug
    state: str | None
    num: int
    question: str
    options: list[str]
    has_images: bool


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00ad", "")
    text = re.sub(r"\s+", " ", text.strip().lower())
    text = re.sub(r"[^\w\säöüß]", "", text)
    return text


def _clean_line(line: str) -> str:
    line = unicodedata.normalize("NFKC", line)
    line = line.replace("\u00ad", "")
    return line.strip()


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def normalize_raw_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"Auf\s*\n\s*gabe", "Aufgabe", text, flags=re.IGNORECASE)
    text = re.sub(r"Seite\s+\d+\s+von\s+\d+", "", text)
    text = re.sub(r"Gesamtfragenkatalog.*?\n", "", text, count=1)
    text = re.sub(r"Stand:\s*\d{2}\.\d{2}\.\d{4}.*?\n", "", text)
    text = re.sub(r"Teil I\s*\n\s*Allgemeine Fragen", "[[TEIL_I]]", text)
    text = re.sub(r"Teil II\s*", "[[TEIL_II]]", text)
    return text


def _is_option_line(line: str) -> bool:
    return bool(OPTION_PREFIX.match(line)) or line.startswith(("Bild 1", "Bild 2", "Bild 3", "Bild 4"))


def _strip_option(line: str) -> str:
    line = _clean_line(line)
    line = OPTION_PREFIX.sub("", line)
    if line.startswith("Bild "):
        return line
    return line.strip()


def parse_questions(text: str) -> list[ParsedQuestion]:
    text = normalize_raw_text(text)
    parts = re.split(r"Aufgabe\s+(\d+)", text)
    # parts[0] = preamble, then pairs (num, body)
    current_part = "general"
    current_state: str | None = None
    out: list[ParsedQuestion] = []

    for i in range(1, len(parts), 2):
        num = int(parts[i])
        body = parts[i + 1] if i + 1 < len(parts) else ""
        if "[[TEIL_II]]" in body:
            current_part = "state"
            body = body.replace("[[TEIL_I]]", "")
            chunks = body.split("[[TEIL_II]]")
            for chunk_i, chunk in enumerate(chunks):
                if chunk_i > 0:
                    m = STATE_LINE.search(chunk)
                    if m:
                        name = m.group(1).strip()
                        for bl in BUNDESLAENDER:
                            if name.lower().startswith(bl.lower()):
                                current_state = bl
                                break
                        else:
                            current_state = name
                    chunk = STATE_LINE.sub("", chunk)
                _parse_block(chunk, current_part, current_state, num if chunk_i == 0 else num, out)
            continue
        if "[[TEIL_I]]" in body:
            current_part = "general"
            current_state = None
            body = body.replace("[[TEIL_I]]", "")
        _parse_one(body, current_part, current_state, num, out)
    return out


def _parse_one(body: str, part: str, state: str | None, num: int, out: list[ParsedQuestion]) -> None:
    lines = [_clean_line(ln) for ln in body.splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith("Bild ") or ln.startswith("Bild 1")]
    # keep Bild 1-4 as options only when prefixed with checkbox later
    lines = [ln for ln in lines if ln not in {"Teil I", "Teil II", "Allgemeine Fragen"}]

    question_lines: list[str] = []
    options: list[str] = []
    opt_buf: list[str] = []
    phase = "question"
    has_images = False

    for ln in lines:
        if ln.startswith("Bild ") and not _is_option_line(ln):
            has_images = True
            continue
        if _is_option_line(ln):
            if opt_buf:
                options.append(" ".join(opt_buf).strip())
                opt_buf = []
            phase = "options"
            opt = _strip_option(ln)
            if opt:
                opt_buf = [opt]
            continue
        if phase == "question":
            if re.match(r"^Frag", ln):
                continue
            question_lines.append(ln)
        elif phase == "options" and len(options) < 3:
            # continuation of last option
            if opt_buf:
                opt_buf.append(ln)
            elif options:
                options[-1] = (options[-1] + " " + ln).strip()
        elif phase == "options" and opt_buf:
            opt_buf.append(ln)

    if opt_buf:
        options.append(" ".join(opt_buf).strip())

    # Some PDF extractions drop checkbox markers — grab trailing 4 non-empty lines
    if len(options) < 2 and len(lines) >= 5:
        options = []
        question_lines = []
        for idx, ln in enumerate(lines):
            if _is_option_line(ln):
                tail = [_strip_option(x) for x in lines[idx:] if _clean_line(x)]
                tail = [t for t in tail if t and not t.startswith("Bild ") or re.match(r"^Bild [1-4]", t)]
                if len(tail) >= 4:
                    options = tail[:4]
                    question_lines = lines[:idx]
                break

    question = " ".join(question_lines).strip()
    question = re.sub(r"\s+", " ", question)
    options = [re.sub(r"\s+", " ", o).strip() for o in options if o.strip()][:4]

    if not question or len(options) < 2:
        return

    out.append(
        ParsedQuestion(
            part=part,
            state=state,
            num=num,
            question=question,
            options=options,
            has_images=has_images or any(o.startswith("Bild ") for o in options),
        )
    )


def _parse_block(body: str, part: str, state: str | None, num: int, out: list[ParsedQuestion]) -> None:
    _parse_one(body, part, state, num, out)


def load_answer_index(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    index: dict[str, dict] = {}
    for item in raw:
        q = _norm(item.get("question", ""))
        if q:
            index[q] = item
        opts = tuple(_norm(item.get(k, "")) for k in "abcd")
        key2 = q + "|" + "|".join(opts[:2])
        index[key2] = item
    return index


def find_source_match(pq: ParsedQuestion, index: dict[str, dict]) -> tuple[dict | None, float]:
    nq = _norm(pq.question)
    best_item: dict | None = None
    best_ratio = 0.0
    for item in index.values():
        iq = _norm(item.get("question", ""))
        if not iq:
            continue
        ratio = SequenceMatcher(None, nq, iq).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_item = item
    if best_ratio >= 0.82 and best_item:
        return best_item, best_ratio
    return None, best_ratio


def align_option_letter(pdf_option: str, source_item: dict) -> str | None:
    target = _norm(pdf_option)
    if not target:
        return None
    best_letter: str | None = None
    best_ratio = 0.0
    for letter in "abcd":
        src = _norm(source_item.get(letter, ""))
        if not src:
            continue
        ratio = SequenceMatcher(None, target, src).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_letter = letter
    return best_letter if best_ratio >= 0.72 else None


def canonical_options(
    pq: ParsedQuestion, source_item: dict | None
) -> tuple[list[str], list[str], str | None]:
    """Align PDF options to source a/b/c/d order so EN translations match."""
    if not source_item:
        return pq.options, [""] * len(pq.options), None

    en = (source_item.get("translation") or {}).get("en", {})
    by_letter: dict[str, tuple[str, str]] = {}
    for opt in pq.options:
        letter = align_option_letter(opt, source_item)
        if letter and letter not in by_letter:
            by_letter[letter] = (opt, en.get(letter, ""))

    for letter in "abcd":
        if letter in by_letter:
            continue
        src_de = source_item.get(letter, "")
        if src_de:
            by_letter[letter] = (src_de, en.get(letter, ""))

    letters = [letter for letter in "abcd" if letter in by_letter]
    opts_de = [by_letter[letter][0] for letter in letters]
    opts_en = [by_letter[letter][1] for letter in letters]
    solution = str(source_item.get("solution", "")).lower() or None
    if solution not in {"a", "b", "c", "d"}:
        solution = None
    return opts_de, opts_en, solution


def question_id(pq: ParsedQuestion) -> str:
    if pq.part == "general":
        return f"general:{pq.num}"
    slug = (pq.state or "unknown").replace(" ", "_")
    return f"{slug}:{pq.num}"


def build_records(parsed: list[ParsedQuestion], index: dict[str, dict]) -> list[dict]:
    records: list[dict] = []
    for pq in parsed:
        source_item, confidence = find_source_match(pq, index)
        opts_de, opts_en, solution = canonical_options(pq, source_item)
        en_q = ""
        if source_item:
            en_q = (source_item.get("translation") or {}).get("en", {}).get("question", "")
        method = "fuzzy" if source_item else "unmatched"
        rec = {
            "id": question_id(pq),
            "part": pq.part,
            "state": pq.state,
            "num": pq.num,
            "question_de": pq.question,
            "question_en": en_q,
            "options_de": opts_de,
            "options_en": opts_en,
            "correct": solution,
            "match_method": method,
            "match_confidence": round(confidence, 3),
            "has_images": pq.has_images,
            "category": pq.state if pq.part == "state" else "Bundesweit",
        }
        records.append(rec)
    return records


def _clean_phrase(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00ad", "")
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"^hier\s+", "", text, flags=re.I)
    return text.strip(" .…,;")


def _extract_terms(text: str) -> list[str]:
    """Pull German vocabulary-sized terms from a line of text."""
    text = _clean_phrase(text)
    if not text:
        return []
    found: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        term = _clean_phrase(term)
        key = _norm(term)
        if not term or key in seen or key in STOPWORDS:
            return
        if len(term) < 4 or len(term) > 64:
            return
        if re.fullmatch(r"[\d%./\-]+", term):
            return
        if term.lower().startswith("bild "):
            return
        # skip bare question words / fragments
        if " " not in term and len(term) < 5 and term.upper() != term:
            return
        seen.add(key)
        found.append(term)

    for quoted in re.findall(r"„([^“]+)“|\"([^\"]+)\"", text):
        add(quoted[0] or quoted[1])

    for match in re.finditer(
        r"\b[A-ZÄÖÜ][A-Za-zäöüßÄÖÜ]+(?:-[A-Za-zäöüßÄÖÜ]+)?(?:\s+[A-ZÄÖÜ][a-zäöüß]+){0,3}\b",
        text,
    ):
        add(match.group())

    return found


OPTION_CORE_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"^hier\s+(.+?)\s+gilt\.?$", re.I), 1),
    (re.compile(r"^(.+?)\s+teilnimmt\.?$", re.I), 1),
    (re.compile(r"^die\s+Menschen\s+(.+?)\s+(?:haben|zahlen)\.?$", re.I), 1),
    (re.compile(r"^der\s+(.+?)\s+ist\.?$", re.I), 1),
    (re.compile(r"^das\s+ist\s+(.+?)\.?$", re.I), 1),
]


def _glossary_en(de: str) -> str:
    if de in LID_GLOSSARY:
        return LID_GLOSSARY[de]
    key = _norm(de)
    for term, en in LID_GLOSSARY.items():
        if _norm(term) == key:
            return en
    return ""


BAD_EN_PREFIX = re.compile(
    r"^(at the|at |in case|people |all residents|only |the state|may only|a voter)",
    re.I,
)


def _strip_leading_article(text: str) -> str:
    return re.sub(
        r"^(der|die|das|den|dem|des|ein|eine|einen|einem|einer|eines)\s+",
        "",
        text,
        flags=re.I,
    )


def _clean_en_option(en_text: str) -> str:
    en_text = _clean_phrase(en_text)
    en_text = re.sub(r"^(the|a|an)\s+", "", en_text, flags=re.I)
    en_text = re.sub(r"\s+(applies here|here)\.?$", "", en_text, flags=re.I)
    return _clean_phrase(en_text)


def _is_good_en_option(en_text: str) -> bool:
    en_text = _clean_en_option(en_text)
    if not en_text or len(en_text) > 56:
        return False
    if en_text.count(" ") > 5:
        return False
    if BAD_EN_PREFIX.match(en_text):
        return False
    return True


def _is_vocab_word(de: str) -> bool:
    """True when text is a word/short term — not a full quiz answer sentence."""
    de = _clean_phrase(de)
    if not de:
        return False
    if de in LID_GLOSSARY or de in BUNDESLAENDER:
        return True
    if "/" in de and len(de) <= 48:
        return not any(w.lower() in VERB_WORDS for w in de.split()) and " im " not in de.lower()
    if "-" in de and de.count(" ") <= 1 and len(de) >= 4:
        return True
    if SENTENCE_START_RE.match(de):
        return False
    if de.lower().startswith(
        ("bei ", "beim ", "an ", "in ", "auf ", "durch ", "von ", "wenn ", "kann ", "er ", "sie ")
    ):
        return False
    words = de.split()
    if len(words) > MAX_VOCAB_WORDS:
        return False
    if any(w.lower() in VERB_WORDS for w in words):
        return False
    if len(words) == 1:
        return len(de) >= 4 and _norm(de) not in GENERIC_SKIP
    return any(len(w) >= 6 or (w[0].isupper() and _norm(w) not in STOPWORDS) for w in words)


def _core_terms_from_option(de_text: str) -> list[str]:
    de_text = _clean_phrase(de_text)
    if not de_text:
        return []

    for pattern, group in OPTION_CORE_PATTERNS:
        m = pattern.match(de_text)
        if m:
            core = _strip_leading_article(_clean_phrase(m.group(group)))
            if _is_vocab_word(core):
                return [core]

    stripped = _strip_leading_article(de_text)
    if stripped in LID_GLOSSARY or stripped in BUNDESLAENDER:
        return [stripped]
    if _is_vocab_word(stripped):
        return [stripped]

    terms: list[str] = []
    seen: set[str] = set()
    for term in _extract_terms(de_text):
        term = _strip_leading_article(term)
        key = _norm(term)
        if key in seen:
            continue
        if _is_vocab_word(term):
            seen.add(key)
            terms.append(term)
    return terms


def _build_auto_glossary(records: list[dict]) -> dict[str, str]:
    votes: dict[str, dict[str, int]] = {}
    for rec in records:
        for de_raw, en_raw in zip(rec.get("options_de") or [], rec.get("options_en") or []):
            en_raw = _clean_en_option(en_raw)
            if not _is_good_en_option(en_raw):
                continue
            for core in _core_terms_from_option(de_raw):
                key = _norm(core)
                if len(core) < 4 or key in STOPWORDS or key in GENERIC_SKIP:
                    continue
                if re.fullmatch(r"[\d%./\-]+", core):
                    continue
                if not _is_vocab_word(core):
                    continue
                votes.setdefault(key, {})
                votes[key][en_raw] = votes[key].get(en_raw, 0) + 1

    auto: dict[str, str] = {}
    for key, en_counts in votes.items():
        en_text, count = max(en_counts.items(), key=lambda item: item[1])
        if count >= 2:
            # recover original casing from first matching record later via glossary merge
            auto[key] = en_text
    return auto


def _english_for_term(de_term: str, en_option: str, auto_glossary: dict[str, str] | None = None) -> str:
    hit = _glossary_en(de_term)
    if hit:
        return hit
    if auto_glossary:
        hit = auto_glossary.get(_norm(de_term), "")
        if hit:
            return hit
    en_option = _clean_en_option(en_option)
    if not _is_good_en_option(en_option):
        return ""
    if de_term.count(" ") <= 2 and len(de_term) <= 36:
        return en_option[:120]
    for term in _extract_terms(en_option):
        if len(term) >= 4:
            return term
    return en_option[:120]


def _split_compound_places(de_text: str) -> list[str]:
    parts = re.split(r"\s+und\s+", de_text, flags=re.I)
    if len(parts) <= 1:
        return [de_text]
    out = [_clean_phrase(p) for p in parts if _clean_phrase(p)]
    if all(p in BUNDESLAENDER or p in LID_GLOSSARY for p in out):
        return out
    return [de_text]


def _vocab_pairs_from_option(
    de_text: str, en_text: str, auto_glossary: dict[str, str] | None = None
) -> list[tuple[str, str]]:
    de_text = _clean_phrase(de_text)
    en_text = _clean_phrase(en_text)
    if not de_text or de_text.lower().startswith("bild "):
        return []
    if SKIP_PHRASE_RE.match(de_text):
        return []
    if len(de_text) > 72 or de_text.count(" ") > 10:
        return []

    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(de: str, en: str) -> None:
        de = _clean_phrase(de)
        en = _clean_phrase(en)
        key = _norm(de)
        if not de or not en or key in seen or key in STOPWORDS or key in GENERIC_SKIP:
            return
        if not _is_vocab_word(de):
            return
        if len(de) < 4 or re.fullmatch(r"[\d%./\-]+", de):
            return
        if _norm(en) == key and not (_glossary_en(de) or (auto_glossary and key in auto_glossary)):
            return
        seen.add(key)
        pairs.append((de, en[:120]))

    for chunk in _split_compound_places(de_text):
        if chunk in LID_GLOSSARY or chunk in BUNDESLAENDER:
            en_val = _english_for_term(chunk, en_text, auto_glossary)
            if en_val:
                add(chunk, en_val)
            continue

        if re.match(r"^(bei |beim |an der |in der |auf der )", chunk, re.I):
            for term in _extract_terms(chunk):
                en_val = _english_for_term(term, en_text, auto_glossary)
                if en_val and (_glossary_en(term) or (auto_glossary and _norm(term) in auto_glossary)):
                    add(term, en_val)
            continue

        for core in _core_terms_from_option(chunk):
            en_val = _english_for_term(core, en_text, auto_glossary)
            if en_val:
                add(core, en_val)

    return pairs


def _pair_terms_de_en(
    de_text: str, en_text: str, auto_glossary: dict[str, str] | None = None
) -> list[tuple[str, str]]:
    return _vocab_pairs_from_option(de_text, en_text, auto_glossary)


def _word_english(de: str, en_pair: str, merged_glossary: dict[str, str]) -> str:
    """Short dictionary gloss for the flashcard front — not the full quiz answer."""
    gloss = _glossary_en(de)
    if gloss:
        return gloss
    key = _norm(de)
    if key in merged_glossary and merged_glossary[key].count(" ") <= 5:
        return merged_glossary[key]
    if en_pair.count(" ") <= 3:
        return en_pair
    return en_pair[:120]


def _build_example_sentences(
    rec: dict, de_term: str, de_option: str = "", en_option: str = ""
) -> tuple[str, str]:
    """Build full DE/EN example sentences from the quiz question + matching option."""
    de_opt = _clean_phrase(de_option)
    en_opt = _clean_phrase(en_option)
    q_de = _clean_phrase(rec.get("question_de", ""))
    q_en = _clean_phrase(rec.get("question_en", ""))

    if de_opt and de_term.lower() in de_opt.lower():
        if re.search(r"(\.\.\.|…)\s*$", q_de) or re.search(r"\s+bei\s*$", q_de, re.I):
            stem = re.sub(r"(\.\.\.|…)\s*$", "", q_de).strip()
            stem = re.sub(r"\s+bei\s*$", "", stem, flags=re.I)
            sent_de = f"{stem} bei {de_opt}"
        elif "…" in q_de or "..." in q_de:
            sent_de = q_de.replace("…", de_opt).replace("...", de_opt)
        else:
            sent_de = de_opt
        if not sent_de.endswith("."):
            sent_de += "."

        if en_opt:
            if re.search(r"(\.\.\.|…)\s*$", q_en) or re.search(r"\s+at\s*$", q_en, re.I):
                stem_en = re.sub(r"(\.\.\.|…)\s*$", "", q_en).strip()
                stem_en = re.sub(r"\s+at\s*$", "", stem_en, flags=re.I)
                sent_en = f"{stem_en} for {en_opt}"
            elif "…" in q_en or "..." in q_en:
                sent_en = q_en.replace("…", en_opt).replace("...", en_opt)
            else:
                sent_en = en_opt
            if not sent_en.endswith("."):
                sent_en += "."
        else:
            sent_en = q_en
        return sent_de, sent_en

    if de_opt:
        sent_de = de_opt if de_opt.endswith(".") else f"{de_opt}."
        sent_en = en_opt if en_opt.endswith(".") else f"{en_opt}." if en_opt else q_en
        return sent_de, sent_en

    return q_de, q_en


def _is_study_phrase(de: str) -> bool:
    if SKIP_PHRASE_RE.match(de):
        return False
    if not _is_vocab_word(de):
        return False
    return True


def extract_word_flashcards(records: list[dict], start_id: int = WORDS_START_ID) -> list[dict]:
    """Extract vocabulary flashcards from PDF answer options and key terms."""
    bucket: dict[str, dict] = {}
    auto_glossary = _build_auto_glossary(records)
    # Prefer stable manual glossary entries over auto-mined text.
    merged_glossary = {**auto_glossary, **{_norm(k): v for k, v in LID_GLOSSARY.items()}}

    def add_pair(
        de: str,
        en: str,
        rec: dict,
        *,
        weight: int = 1,
        de_option: str = "",
        en_option: str = "",
    ) -> None:
        de = _clean_phrase(de)
        en = _clean_phrase(en)
        if not _is_study_phrase(de):
            return
        if re.fullmatch(r"[\d%./\-]+", de):
            return
        if de.lower().startswith(("bei der ", "bei den ", "beim ", "an der ", "in der ", "auf der ")):
            return
        key = _norm(de)
        if not key or key in STOPWORDS or key in GENERIC_SKIP:
            return
        en_word = _word_english(de, en, merged_glossary)
        if not en_word:
            return
        if en_word.count(" ") > 5 and not (_glossary_en(de) or key in merged_glossary):
            return
        if _norm(en_word) == key and not (_glossary_en(de) or key in merged_glossary):
            return
        sent_de, sent_en = _build_example_sentences(rec, de, de_option, en_option)
        prev = bucket.get(key)
        if prev:
            prev["count"] += weight
            if weight >= prev.get("best_weight", 0):
                prev["best_weight"] = weight
                prev["sentence_de"] = sent_de
                prev["sentence_en"] = sent_en
            return
        bucket[key] = {
            "german": de,
            "english": en_word[:120],
            "sentence_de": sent_de,
            "sentence_en": sent_en,
            "count": weight,
            "best_weight": weight,
        }

    for rec in records:
        opts_de = rec.get("options_de") or []
        opts_en = rec.get("options_en") or []
        correct = (rec.get("correct") or "").lower()

        for i, de_raw in enumerate(opts_de):
            en_raw = _clean_phrase(opts_en[i]) if i < len(opts_en) else ""
            weight = 3 if correct and i == ord(correct) - ord("a") else 1
            for de, en in _pair_terms_de_en(de_raw, en_raw, merged_glossary):
                add_pair(de, en, rec, weight=weight, de_option=de_raw, en_option=en_raw)

        for term in _extract_terms(rec["question_de"]):
            if not (_glossary_en(term) or term in BUNDESLAENDER):
                continue
            add_pair(
                term,
                _english_for_term(term, "", merged_glossary),
                rec,
                weight=1,
            )

    ranked = [item for item in bucket.values() if item["count"] >= 1]
    ranked.sort(key=lambda x: (-x["count"], x["german"]))

    cards: list[dict] = []
    wid = start_id
    for item in ranked:
        cards.append(
            {
                "id": wid,
                "section": SECTION_WORDS,
                "german": item["german"],
                "english": item["english"],
                "pronunciation": item["german"],
                "sentence_de": item["sentence_de"],
                "sentence_en": item["sentence_en"],
                "image_query": item["german"][:40],
                "has_image": False,
            }
        )
        wid += 1
    return cards


def extract_vocabulary(records: list[dict], start_id: int = WORDS_START_ID) -> list[dict]:
    """Create word flashcards grouped under Leben deutsch words."""
    return extract_word_flashcards(records, start_id=start_id)


def merge_vocab_into_a1(cards: list[dict]) -> None:
    vocab_path = ROOT / "data" / "levels" / "a1" / "vocabulary.json"
    data = json.loads(vocab_path.read_text(encoding="utf-8"))
    words = [
        w
        for w in data["words"]
        if not str(w.get("section", "")).startswith(SECTION_LID_PREFIX)
        and str(w.get("section", "")) != SECTION_WORDS
    ]
    words.extend(cards)
    data["words"] = words
    vocab_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    pdf_path = DEFAULT_PDF if DEFAULT_PDF.exists() else FALLBACK_PDF
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = extract_pdf_text(pdf_path)
    parsed = parse_questions(text)
    index = load_answer_index(ANSWERS_SOURCE)
    records = build_records(parsed, index)

    matched = sum(1 for r in records if (r.get("correct") or "").lower() in ("a", "b", "c", "d"))
    payload = {
        "version": 1,
        "source_pdf": str(pdf_path),
        "total": len(records),
        "matched_answers": matched,
        "questions": records,
    }
    QUESTIONS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    cards = extract_vocabulary(records)
    VOCAB_OUT.write_text(json.dumps({"words": cards}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    merge_vocab_into_a1(cards)

    print(f"Parsed {len(parsed)} questions from PDF")
    print(f"Matched answers: {matched}/{len(records)}")
    print(f"Vocabulary word cards: {len(cards)} in '{SECTION_WORDS}'")
    print(f"Wrote {QUESTIONS_JSON}")
    print(f"Merged '{SECTION_WORDS}' into a1/vocabulary.json")


if __name__ == "__main__":
    main()
