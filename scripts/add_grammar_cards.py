#!/usr/bin/env python3
"""Append A1 grammar flashcards to data/levels/a1/vocabulary.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOCAB = ROOT / "data" / "levels" / "a1" / "vocabulary.json"
SECTION_PREFIX = "16. Grammar"
START_ID = 500

GRAMMAR_CARDS: list[dict] = [
    # — Präsens —
    {
        "german": "Präsens — present tense",
        "english": "German has no “I am eating” form — Präsens covers present AND continuous",
        "sentence_de": "Ich esse. = I eat / I am eating.",
        "sentence_en": "Use Präsens for both habits and right now.",
    },
    {
        "german": "Regular verb endings",
        "english": "ich -e · du -st · er/sie/es -t · wir -en · ihr -t · sie/Sie -en",
        "sentence_de": "ich mache · du machst · er macht · wir machen",
        "sentence_en": "Remove -en from infinitive, add the ending.",
    },
    {
        "german": "sein — to be",
        "english": "ich bin · du bist · er/sie/es ist · wir sind · ihr seid · sie/Sie sind",
        "sentence_de": "Ich bin müde. Du bist nett.",
        "sentence_en": "I am tired. You are nice.",
    },
    {
        "german": "haben — to have",
        "english": "ich habe · du hast · er/sie/es hat · wir haben · ihr habt · sie/Sie haben",
        "sentence_de": "Ich habe Zeit. Hast du Hunger?",
        "sentence_en": "I have time. Are you hungry?",
    },
    {
        "german": "Stem-change verbs (du / er)",
        "english": "Vowel changes in du & er/sie/es forms — memorize as a pair",
        "sentence_de": "fahren → du fährst, er fährt · lesen → du liest, er liest",
        "sentence_en": "Also: essen → isst, schlafen → schläft, sprechen → spricht",
    },
    {
        "german": "machen — to do/make",
        "english": "ich mache · du machst · er macht · wir machen · ihr macht · sie machen",
        "sentence_de": "Was machst du heute?",
        "sentence_en": "What are you doing today?",
    },
    {
        "german": "lernen — to learn",
        "english": "ich lerne · du lernst · er lernt · wir lernen",
        "sentence_de": "Ich lerne Deutsch.",
        "sentence_en": "I am learning German.",
    },
    {
        "german": "wohnen — to live (reside)",
        "english": "ich wohne · du wohnst · er wohnt · wir wohnen",
        "sentence_de": "Ich wohne in Berlin.",
        "sentence_en": "I live in Berlin.",
    },
    # — Word order & questions —
    {
        "german": "Rule: verb in position 2",
        "english": "In a normal sentence the conjugated verb is always the 2nd element",
        "sentence_de": "Heute lerne ich Deutsch. / Ich lerne heute Deutsch.",
        "sentence_en": "Today I learn German. / I learn German today.",
    },
    {
        "german": "Yes/No question",
        "english": "Put the conjugated verb first",
        "sentence_de": "Lernst du Deutsch? · Hast du Zeit?",
        "sentence_en": "Do you learn German? · Do you have time?",
    },
    {
        "german": "W-question",
        "english": "Question word + verb + subject (+ rest)",
        "sentence_de": "Wo wohnst du? · Was machst du? · Wann kommst du?",
        "sentence_en": "Where do you live? · What are you doing? · When are you coming?",
    },
    {
        "german": "Modal + infinitive at the END",
        "english": "Modal verb is conjugated; main verb stays in infinitive at the end",
        "sentence_de": "Ich kann Deutsch sprechen. · Ich muss arbeiten.",
        "sentence_en": "I can speak German. · I must work.",
    },
    # — Modals —
    {
        "german": "können — can / to be able to",
        "english": "ich kann · du kannst · er kann · wir können · ihr könnt · sie können",
        "sentence_de": "Ich kann schwimmen.",
        "sentence_en": "I can swim.",
    },
    {
        "german": "müssen — must / to have to",
        "english": "ich muss · du musst · er muss · wir müssen · ihr müsst · sie müssen",
        "sentence_de": "Ich muss lernen.",
        "sentence_en": "I have to study.",
    },
    {
        "german": "wollen — to want",
        "english": "ich will · du willst · er will · wir wollen · ihr wollt · sie wollen",
        "sentence_de": "Ich will Kaffee trinken.",
        "sentence_en": "I want to drink coffee.",
    },
    {
        "german": "dürfen — may / to be allowed",
        "english": "ich darf · du darfst · er darf · wir dürfen · ihr dürft · sie dürfen",
        "sentence_de": "Darf ich hereinkommen?",
        "sentence_en": "May I come in?",
    },
    {
        "german": "sollen — should / to be supposed to",
        "english": "ich soll · du sollst · er soll · wir sollen · ihr sollt · sie sollen",
        "sentence_de": "Ich soll mehr lernen.",
        "sentence_en": "I am supposed to study more.",
    },
    {
        "german": "mögen — to like",
        "english": "ich mag · du magst · er mag · wir mögen · ihr mögt · sie mögen",
        "sentence_de": "Ich mag Pizza.",
        "sentence_en": "I like pizza.",
    },
    # — Perfekt —
    {
        "german": "Perfekt — spoken past",
        "english": "haben or sein (conjugated) + Partizip II at the END",
        "sentence_de": "Ich habe gelernt. · Ich bin gegangen.",
        "sentence_en": "I learned. · I went.",
    },
    {
        "german": "Partizip II — regular verbs",
        "english": "ge- + stem + -t (written at end of sentence)",
        "sentence_de": "machen → gemacht · lernen → gelernt · kaufen → gekauft",
        "sentence_en": "Ich habe gemacht. · Ich habe gelernt.",
    },
    {
        "german": "Partizip II — verbs in -ieren",
        "english": "No ge- prefix — just -t",
        "sentence_de": "studieren → studiert · telefonieren → telefoniert",
        "sentence_en": "Ich habe studiert.",
    },
    {
        "german": "Partizip II — strong verbs",
        "english": "ge- + changed stem + -en (memorize each verb)",
        "sentence_de": "gehen → gegangen · essen → gegessen · schlafen → geschlafen",
        "sentence_en": "Ich bin gegangen. · Ich habe gegessen.",
    },
    {
        "german": "Perfekt with sein",
        "english": "Movement & change of state → use sein (not haben)",
        "sentence_de": "gehen, kommen, fahren, fliegen, bleiben, werden → sein",
        "sentence_en": "Ich bin gekommen. · Ich bin geblieben.",
    },
    {
        "german": "Perfekt with haben",
        "english": "Most other verbs → use haben",
        "sentence_de": "Ich habe gelernt. · Ich habe Pizza gegessen.",
        "sentence_en": "I learned. · I ate pizza.",
    },
    {
        "german": "Perfekt pair: gehen",
        "english": "gehen → bin gegangen",
        "sentence_de": "Gestern bin ich nach Hause gegangen.",
        "sentence_en": "Yesterday I went home.",
    },
    {
        "german": "Perfekt pair: essen",
        "english": "essen → habe gegessen",
        "sentence_de": "Ich habe zu Mittag gegessen.",
        "sentence_en": "I ate lunch.",
    },
    {
        "german": "Perfekt pair: machen",
        "english": "machen → habe gemacht",
        "sentence_de": "Was hast du gestern gemacht?",
        "sentence_en": "What did you do yesterday?",
    },
    # — Präteritum (A1 basics) —
    {
        "german": "Präteritum — sein",
        "english": "ich war · du warst · er war · wir waren · ihr wart · sie waren",
        "sentence_de": "Ich war müde.",
        "sentence_en": "I was tired.",
    },
    {
        "german": "Präteritum — haben",
        "english": "ich hatte · du hattest · er hatte · wir hatten · ihr hattet · sie hatten",
        "sentence_de": "Ich hatte keine Zeit.",
        "sentence_en": "I had no time.",
    },
    {
        "german": "Präteritum — modals (example)",
        "english": "können → ich konnte · du konntest · er konnte",
        "sentence_de": "Ich konnte nicht kommen.",
        "sentence_en": "I couldn't come.",
    },
    # — Other A1 patterns —
    {
        "german": "Separable verb",
        "english": "Prefix splits off and goes to the END in present tense",
        "sentence_de": "aufstehen → Ich stehe um 7 Uhr auf.",
        "sentence_en": "I get up at 7 o'clock.",
    },
    {
        "german": "Accusative — den / die / das",
        "english": "Direct object often changes der → den; die/das stay the same",
        "sentence_de": "Ich sehe den Mann. · Ich kaufe das Buch.",
        "sentence_en": "I see the man. · I buy the book.",
    },
    {
        "german": "nicht vs kein",
        "english": "nicht = not (verbs/adjectives) · kein = no/not a (nouns)",
        "sentence_de": "Ich arbeite nicht. · Ich habe kein Auto.",
        "sentence_en": "I don't work. · I don't have a car.",
    },
    {
        "german": "Time: am / um / im",
        "english": "am Montag · um 8 Uhr · im Sommer",
        "sentence_de": "Am Montag um 8 Uhr fahre ich zur Arbeit.",
        "sentence_en": "On Monday at 8 o'clock I go to work.",
    },
    {
        "german": "Imperative — du",
        "english": "Often the stem: Komm! · Lern! · Mach!",
        "sentence_de": "Komm bitte! · Mach die Tür zu!",
        "sentence_en": "Please come! · Close the door!",
    },
    {
        "german": "Imperative — Sie (formal)",
        "english": "Infinitive + Sie: Kommen Sie! · Lernen Sie!",
        "sentence_de": "Kommen Sie bitte herein.",
        "sentence_en": "Please come in.",
    },
    # — Daily drills —
    {
        "german": "Drill 1 — introduce yourself",
        "english": "Say who you are",
        "sentence_de": "Ich heiße … · Ich bin … Jahre alt.",
        "sentence_en": "My name is … · I am … years old.",
    },
    {
        "german": "Drill 2 — where you live",
        "english": "Präsens + place",
        "sentence_de": "Ich wohne in … .",
        "sentence_en": "I live in …",
    },
    {
        "german": "Drill 3 — what you learn",
        "english": "Präsens daily habit",
        "sentence_de": "Ich lerne Deutsch.",
        "sentence_en": "I am learning German.",
    },
    {
        "german": "Drill 4 — yesterday (Perfekt)",
        "english": "Past with haben/sein + Partizip II",
        "sentence_de": "Gestern habe ich … gemacht. / Gestern bin ich … gegangen.",
        "sentence_en": "Yesterday I did … / Yesterday I went …",
    },
    {
        "german": "Drill 5 — tomorrow (modal)",
        "english": "Future plan with wollen/werden/müssen",
        "sentence_de": "Morgen will ich … · Morgen muss ich …",
        "sentence_en": "Tomorrow I want to … · Tomorrow I must …",
    },
]


def subsection(title: str) -> str:
    return f"{SECTION_PREFIX} — {title}"


def assign_sections(cards: list[dict]) -> None:
    """Tag cards with grammar sub-sections for sidebar filtering."""
    ranges = [
        (0, 8, "Präsens"),
        (8, 12, "Word order"),
        (12, 19, "Modals"),
        (19, 27, "Perfekt"),
        (27, 30, "Präteritum"),
        (30, 36, "Patterns"),
        (36, 41, "Daily drills"),
    ]
    for start, end, name in ranges:
        for card in cards[start:end]:
            card["_subsection"] = name


def main() -> None:
    data = json.loads(VOCAB.read_text(encoding="utf-8"))
    words: list[dict] = data["words"]

    existing_ids = {w["id"] for w in words}
    if any(w.get("section", "").startswith(SECTION_PREFIX) for w in words):
        print("Grammar section already present — remove section 16 entries to re-run.")
        return

    if START_ID in existing_ids:
        raise SystemExit(f"ID {START_ID} already in use — pick a new START_ID.")

    assign_sections(GRAMMAR_CARDS)
    next_id = START_ID
    for raw in GRAMMAR_CARDS:
        sub = raw.pop("_subsection", "Grammar")
        words.append(
            {
                "id": next_id,
                "section": f"{SECTION_PREFIX} — {sub}",
                "german": raw["german"],
                "english": raw["english"],
                "pronunciation": raw["german"].split("—")[0].strip()[:40],
                "sentence_de": raw["sentence_de"],
                "sentence_en": raw["sentence_en"],
                "image_query": "",
                "has_image": False,
            }
        )
        next_id += 1

    data["words"] = words
    VOCAB.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Added {len(GRAMMAR_CARDS)} grammar cards (ids {START_ID}–{next_id - 1})")


if __name__ == "__main__":
    main()
