#!/usr/bin/env python3
"""Build data/levels/a2/vocabulary.json — run once or after editing A2 word data below."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from a1.articles import article_for_german, german_with_article
from a1.images import image_queries_for
from a1.levels import ensure_level_layout, vocabulary_path

# (section, german, english) — extend this list to grow A2
A2_ENTRIES: list[tuple[str, str, str]] = [
    # 1. Perfekt — past participles & auxiliaries
    ("1. Perfekt (past tense)", "haben", "to have (auxiliary)"),
    ("1. Perfekt (past tense)", "sein", "to be (auxiliary)"),
    ("1. Perfekt (past tense)", "gegangen", "gone (past participle)"),
    ("1. Perfekt (past tense)", "gekommen", "come (past participle)"),
    ("1. Perfekt (past tense)", "gemacht", "done/made (past participle)"),
    ("1. Perfekt (past tense)", "gesehen", "seen (past participle)"),
    ("1. Perfekt (past tense)", "gegessen", "eaten (past participle)"),
    ("1. Perfekt (past tense)", "getrunken", "drunk (past participle)"),
    ("1. Perfekt (past tense)", "geschrieben", "written (past participle)"),
    ("1. Perfekt (past tense)", "gelesen", "read (past participle)"),
    ("1. Perfekt (past tense)", "gefahren", "driven/traveled (past participle)"),
    ("1. Perfekt (past tense)", "geflogen", "flown (past participle)"),
    ("1. Perfekt (past tense)", "genommen", "taken (past participle)"),
    ("1. Perfekt (past tense)", "gegeben", "given (past participle)"),
    ("1. Perfekt (past tense)", "gekauft", "bought (past participle)"),
    ("1. Perfekt (past tense)", "gestern", "yesterday"),
    ("1. Perfekt (past tense)", "schon", "already"),
    ("1. Perfekt (past tense)", "noch nicht", "not yet"),
    ("1. Perfekt (past tense)", "gerade", "just / right now"),
    ("1. Perfekt (past tense)", "Ich habe … gemacht", "I have done …"),
    # 2. Reflexive verbs
    ("2. Reflexive verbs", "sich waschen", "to wash oneself"),
    ("2. Reflexive verbs", "sich anziehen", "to get dressed"),
    ("2. Reflexive verbs", "sich ausruhen", "to rest"),
    ("2. Reflexive verbs", "sich freuen", "to be glad"),
    ("2. Reflexive verbs", "sich interessieren", "to be interested"),
    ("2. Reflexive verbs", "sich erinnern", "to remember"),
    ("2. Reflexive verbs", "sich vorstellen", "to introduce oneself / imagine"),
    ("2. Reflexive verbs", "sich beeilen", "to hurry"),
    ("2. Reflexive verbs", "sich fühlen", "to feel"),
    ("2. Reflexive verbs", "sich setzen", "to sit down"),
    ("2. Reflexive verbs", "sich legen", "to lie down"),
    ("2. Reflexive verbs", "sich treffen", "to meet (each other)"),
    # 3. Comparisons
    ("3. Comparisons", "größer", "bigger"),
    ("3. Comparisons", "kleiner", "smaller"),
    ("3. Comparisons", "besser", "better"),
    ("3. Comparisons", "schlechter", "worse"),
    ("3. Comparisons", "schneller", "faster"),
    ("3. Comparisons", "langsamer", "slower"),
    ("3. Comparisons", "teurer", "more expensive"),
    ("3. Comparisons", "billiger", "cheaper"),
    ("3. Comparisons", "am besten", "best (superlative)"),
    ("3. Comparisons", "am schlechtesten", "worst"),
    ("3. Comparisons", "als", "than"),
    ("3. Comparisons", "so … wie", "as … as"),
    ("3. Comparisons", "viel", "much / a lot"),
    ("3. Comparisons", "wenig", "little / few"),
    ("3. Comparisons", "mehr", "more"),
    ("3. Comparisons", "weniger", "less"),
    # 4. Dative case
    ("4. Dative case", "mir", "me (dative)"),
    ("4. Dative case", "dir", "you (dative)"),
    ("4. Dative case", "ihm", "him (dative)"),
    ("4. Dative case", "ihr", "her (dative)"),
    ("4. Dative case", "uns", "us (dative)"),
    ("4. Dative case", "euch", "you all (dative)"),
    ("4. Dative case", "ihnen", "them (dative)"),
    ("4. Dative case", "Ihnen", "you (formal, dative)"),
    ("4. Dative case", "dem Mann", "the man (dative)"),
    ("4. Dative case", "der Frau", "the woman (dative)"),
    ("4. Dative case", "dem Kind", "the child (dative)"),
    ("4. Dative case", "helfen", "to help (+ dative)"),
    ("4. Dative case", "danken", "to thank (+ dative)"),
    ("4. Dative case", "gehören", "to belong to (+ dative)"),
    ("4. Dative case", "gefallen", "to please / like (+ dative)"),
    # 5. Dative prepositions
    ("5. Dative prepositions", "mit", "with"),
    ("5. Dative prepositions", "nach", "after / to (city/country)"),
    ("5. Dative prepositions", "aus", "from / out of"),
    ("5. Dative prepositions", "bei", "at / near / with"),
    ("5. Dative prepositions", "von", "from / of"),
    ("5. Dative prepositions", "zu", "to (person/event)"),
    ("5. Dative prepositions", "seit", "since / for (time)"),
    ("5. Dative prepositions", "gegenüber", "opposite / across from"),
    ("5. Dative prepositions", "ab", "from (starting point)"),
    # 6. Health & body
    ("6. Health & body", "Kopfschmerzen", "headache"),
    ("6. Health & body", "Fieber", "fever"),
    ("6. Health & body", "Husten", "cough"),
    ("6. Health & body", "Schnupfen", "cold (runny nose)"),
    ("6. Health & body", "Arzt", "doctor"),
    ("6. Health & body", "Ärztin", "doctor (female)"),
    ("6. Health & body", "Apotheke", "pharmacy"),
    ("6. Health & body", "Medikament", "medicine"),
    ("6. Health & body", "Rezept", "prescription"),
    ("6. Health & body", "Termin", "appointment"),
    ("6. Health & body", "Rücken", "back"),
    ("6. Health & body", "Bauch", "stomach / belly"),
    ("6. Health & body", "Hals", "throat / neck"),
    ("6. Health & body", "sich fühlen", "to feel"),
    ("6. Health & body", "krank", "sick"),
    ("6. Health & body", "gesund", "healthy"),
    # 7. Work & education
    ("7. Work & education", "Beruf", "profession / job"),
    ("7. Work & education", "Kollege", "colleague (male)"),
    ("7. Work & education", "Kollegin", "colleague (female)"),
    ("7. Work & education", "Chef", "boss (male)"),
    ("7. Work & education", "Chefin", "boss (female)"),
    ("7. Work & education", "Gehalt", "salary"),
    ("7. Work & education", "Bewerbung", "application (job)"),
    ("7. Work & education", "Vorstellungsgespräch", "job interview"),
    ("7. Work & education", "Universität", "university"),
    ("7. Work & education", "Prüfung", "exam"),
    ("7. Work & education", "Note", "grade"),
    ("7. Work & education", "Hausaufgaben", "homework"),
    ("7. Work & education", "Vortrag", "lecture / talk"),
    ("7. Work & education", "Erfahrung", "experience"),
    # 8. Travel & accommodation
    ("8. Travel & accommodation", "Reisebüro", "travel agency"),
    ("8. Travel & accommodation", "Gepäck", "luggage"),
    ("8. Travel & accommodation", "Reisepass", "passport"),
    ("8. Travel & accommodation", "Visum", "visa"),
    ("8. Travel & accommodation", "Abfahrt", "departure"),
    ("8. Travel & accommodation", "Ankunft", "arrival"),
    ("8. Travel & accommodation", "Verspätung", "delay"),
    ("8. Travel & accommodation", "Umsteigen", "to change (trains)"),
    ("8. Travel & accommodation", "einchecken", "to check in"),
    ("8. Travel & accommodation", "auschecken", "to check out"),
    ("8. Travel & accommodation", "Reservierung", "reservation"),
    ("8. Travel & accommodation", "Einzelzimmer", "single room"),
    ("8. Travel & accommodation", "Doppelzimmer", "double room"),
    ("8. Travel & accommodation", "Aussicht", "view"),
    # 9. Feelings & opinions
    ("9. Feelings & opinions", "glücklich", "happy"),
    ("9. Feelings & opinions", "traurig", "sad"),
    ("9. Feelings & opinions", "nervös", "nervous"),
    ("9. Feelings & opinions", "aufgeregt", "excited"),
    ("9. Feelings & opinions", "langweilig", "boring"),
    ("9. Feelings & opinions", "interessant", "interesting"),
    ("9. Feelings & opinions", "Meinung", "opinion"),
    ("9. Feelings & opinions", "glauben", "to believe"),
    ("9. Feelings & opinions", "finden", "to find / think"),
    ("9. Feelings & opinions", "hoffen", "to hope"),
    ("9. Feelings & opinions", "wünschen", "to wish"),
    ("9. Feelings & opinions", "zufrieden", "satisfied"),
    ("9. Feelings & opinions", "enttäuscht", "disappointed"),
    # 10. Conjunctions & clauses
    ("10. Conjunctions", "weil", "because"),
    ("10. Conjunctions", "dass", "that (conjunction)"),
    ("10. Conjunctions", "wenn", "if / when"),
    ("10. Conjunctions", "ob", "whether"),
    ("10. Conjunctions", "als", "when (past) / as"),
    ("10. Conjunctions", "obwohl", "although"),
    ("10. Conjunctions", "deshalb", "therefore"),
    ("10. Conjunctions", "trotzdem", "nevertheless"),
    ("10. Conjunctions", "damit", "so that"),
    ("10. Conjunctions", "bevor", "before"),
    ("10. Conjunctions", "nachdem", "after"),
    # 11. Media & communication
    ("11. Media & communication", "Nachrichten", "news"),
    ("11. Media & communication", "Zeitung", "newspaper"),
    ("11. Media & communication", "Zeitschrift", "magazine"),
    ("11. Media & communication", "Fernsehen", "television"),
    ("11. Media & communication", "Sendung", "broadcast / show"),
    ("11. Media & communication", "Internet", "internet"),
    ("11. Media & communication", "E-Mail", "email"),
    ("11. Media & communication", "Nachricht", "message"),
    ("11. Media & communication", "anrufen", "to call (phone)"),
    ("11. Media & communication", "auflegen", "to hang up"),
    ("11. Media & communication", "verbinden", "to connect / put through"),
    # 12. Household & services
    ("12. Household & services", "Waschmaschine", "washing machine"),
    ("12. Household & services", "Staubsauger", "vacuum cleaner"),
    ("12. Household & services", "Müll", "trash / garbage"),
    ("12. Household & services", "recyceln", "to recycle"),
    ("12. Household & services", "Reparatur", "repair"),
    ("12. Household & services", "Handwerker", "craftsman / tradesperson"),
    ("12. Household & services", "Miete", "rent"),
    ("12. Household & services", "Nebenkosten", "utilities / service charges"),
    ("12. Household & services", "Kaution", "deposit (rental)"),
    ("12. Household & services", "Umzug", "move (relocation)"),
    # 13. Environment & nature
    ("13. Environment", "Umwelt", "environment"),
    ("13. Environment", "Klima", "climate"),
    ("13. Environment", "Verschmutzung", "pollution"),
    ("13. Environment", "Energie", "energy"),
    ("13. Environment", "Wald", "forest"),
    ("13. Environment", "Fluss", "river"),
    ("13. Environment", "Berg", "mountain"),
    ("13. Environment", "See", "lake"),
    ("13. Environment", "Insel", "island"),
    ("13. Environment", "Wetterbericht", "weather forecast"),
    # 14. Useful A2 verbs
    ("14. Useful A2 verbs", "werden", "to become"),
    ("14. Useful A2 verbs", "bleiben", "to stay / remain"),
    ("14. Useful A2 verbs", "brauchen", "to need"),
    ("14. Useful A2 verbs", "bekommen", "to receive / get"),
    ("14. Useful A2 verbs", "kosten", "to cost"),
    ("14. Useful A2 verbs", "passieren", "to happen"),
    ("14. Useful A2 verbs", "bedeuten", "to mean"),
    ("14. Useful A2 verbs", "erklären", "to explain"),
    ("14. Useful A2 verbs", "vergessen", "to forget"),
    ("14. Useful A2 verbs", "verlieren", "to lose"),
    ("14. Useful A2 verbs", "gewinnen", "to win"),
    ("14. Useful A2 verbs", "einkaufen", "to shop"),
    ("14. Useful A2 verbs", "verkaufen", "to sell"),
    ("14. Useful A2 verbs", "leihen", "to lend / borrow"),
    ("14. Useful A2 verbs", "schicken", "to send"),
    ("14. Useful A2 verbs", "empfangen", "to receive"),
    ("14. Useful A2 verbs", "verbieten", "to forbid"),
    ("14. Useful A2 verbs", "erlauben", "to allow"),
    ("14. Useful A2 verbs", "empfehlen", "to recommend"),
    ("14. Useful A2 verbs", "sich entscheiden", "to decide"),
]


def _sentence_de(german: str, english: str) -> str:
    return f"Das Wort ist „{german}“. Das bedeutet: {english.split('(')[0].strip()}."


def _sentence_en(german: str, english: str) -> str:
    return f"The word is „{german}“. It means: {english.split('(')[0].strip()}."


def build_words() -> list[dict]:
    words: list[dict] = []
    for i, (section, german, english) in enumerate(A2_ENTRIES, start=1):
        art = article_for_german(german, section=section)
        de_label = german_with_article(german, article=art)
        queries = image_queries_for(german, english, section=section)
        q = queries[0] if queries else ""
        has_img = bool(queries)
        entry = {
            "id": i,
            "section": section,
            "german": german,
            "english": english,
            "pronunciation": de_label if art else german,
            "sentence_de": _sentence_de(german, english),
            "sentence_en": _sentence_en(german, english),
            "image_query": q,
            "has_image": has_img,
        }
        if art:
            entry["article"] = art
        words.append(entry)
    return words


def main() -> None:
    ensure_level_layout()
    out = vocabulary_path("a2")
    words = build_words()
    out.write_text(json.dumps({"words": words}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(words)} A2 words → {out}")


if __name__ == "__main__":
    main()
