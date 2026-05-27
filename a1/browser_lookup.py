from __future__ import annotations

import base64
import json
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

_DOM_JS = """
function a1SetInput(labelPart, value) {
  const root = window.top.document;
  for (const block of root.querySelectorAll('[data-testid="stTextInput"], [data-testid="stTextArea"]')) {
    const label = block.querySelector("label, p");
    const input = block.querySelector("input, textarea");
    if (!label || !input) continue;
    if (!label.textContent.toLowerCase().includes(labelPart.toLowerCase())) continue;
    const proto = input.tagName === "TEXTAREA"
      ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(input, value);
    else input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }
  return false;
}
"""

_TRANSLATE_JS = """
async function a1Translate(text, sl, tl) {
  const tries = [
    async () => {
      const u = "https://translate.googleapis.com/translate_a/single?client=gtx&sl="
        + sl + "&tl=" + tl + "&dt=t&q=" + encodeURIComponent(text);
      const r = await fetch(u);
      if (!r.ok) throw new Error("google");
      const d = await r.json();
      return (d[0] || []).map(x => x[0]).join("").trim();
    },
    async () => {
      const u = "https://api.mymemory.translated.net/get?q="
        + encodeURIComponent(text) + "&langpair=" + sl + "|" + tl;
      const r = await fetch(u);
      if (!r.ok) throw new Error("mymemory");
      const d = await r.json();
      let t = (d.responseData && d.responseData.translatedText) || "";
      return t.split(/MYMEMORY WARNING/i)[0].trim();
    },
  ];
  for (const fn of tries) {
    try {
      const out = await fn();
      if (out) return out;
    } catch (e) {}
  }
  throw new Error("failed");
}
"""

_SENTENCE_JS = """
async function firstSentencePair(german, english) {
  try {
    const resp = await fetch(
      "https://tatoeba.org/en/api_v0/search?from=deu&to=eng&query="
        + encodeURIComponent(german) + "&sort=relevance"
    );
    if (resp.ok) {
      const data = await resp.json();
      for (const item of (data.results || []).slice(0, 6)) {
        const de = (item.text || "").trim();
        if (!de) continue;
        let en = "";
        try {
          const tr = await fetch(
            "https://tatoeba.org/en/api_v0/sentence_translations/" + item.id
          );
          if (tr.ok) {
            const td = await tr.json();
            const hit = (td.results || []).find(r => r.lang === "eng" || r.lang === "en");
            if (hit) en = (hit.text || "").trim();
          }
        } catch (e) {}
        if (!en) try { en = await a1Translate(de, "de", "en"); } catch (e) {}
        if (de && en) return { de, en };
      }
    }
  } catch (e) {}
  for (const de of ["Das ist " + german + ".", "Das Wort ist „" + german + "“."]) {
    try {
      const en = await a1Translate(de, "de", "en");
      if (en) return { de, en };
    } catch (e) {}
  }
  return null;
}
"""

_FIELD_LABELS = {
    "add_english": "english meaning",
    "add_german": "german word",
}


def _run_st_javascript(code: str, *, key: str) -> Any:
    try:
        from streamlit_javascript import st_javascript
    except ImportError:
        return "__NO_JS_LIB__"
    return st_javascript(code, key=f"a1_{key}")


def _is_pending(value: Any) -> bool:
    return value is None or value == 0


def _translate_js(text: str, source: str, target: str) -> str:
    return f"""
    {_TRANSLATE_JS}
    (async () => {{
      try {{ return await a1Translate({json.dumps(text)}, {json.dumps(source)}, {json.dumps(target)}); }}
      catch (e) {{ return ""; }}
    }})()
    """


def _try_server_translate(text: str, source: str, target: str) -> str | None:
    try:
        from a1.lookup import translate_text

        return translate_text(text, source, target)
    except Exception:
        return None


def _render_inline_translation(text: str, source: str, target: str, field: str) -> None:
    label = _FIELD_LABELS.get(field, field)
    components.html(
        f"""
        <style>body {{ margin:0; font:0.85rem sans-serif; color:#666; }}</style>
        <div id="s">Looking up…</div>
        <script>{_DOM_JS}</script>
        <script>{_TRANSLATE_JS}</script>
        <script>
        (async () => {{
          const status = document.getElementById("s");
          try {{
            const tr = await a1Translate({json.dumps(text)}, {json.dumps(source)}, {json.dumps(target)});
            if (a1SetInput({json.dumps(label)}, tr)) {{
              status.textContent = "Filled in: " + tr;
              status.style.color = "#0f3d2e";
            }} else {{
              status.textContent = "Found: " + tr + " — copy into the field above.";
            }}
          }} catch (e) {{
            status.textContent = "Lookup failed — check internet/VPN.";
            status.style.color = "#c0392b";
          }}
        }})();
        </script>
        """,
        height=34,
        scrolling=False,
    )


def _render_inline_sentences(german: str, english: str) -> None:
    components.html(
        f"""
        <style>body {{ margin:0; font:0.85rem sans-serif; color:#666; }}</style>
        <div id="s">Searching…</div>
        <script>{_DOM_JS}</script>
        <script>{_TRANSLATE_JS}</script>
        <script>{_SENTENCE_JS}</script>
        <script>
        (async () => {{
          const status = document.getElementById("s");
          try {{
            const pair = await firstSentencePair({json.dumps(german)}, {json.dumps(english)});
            if (!pair) throw new Error("none");
            a1SetInput("german example", pair.de);
            a1SetInput("english example", pair.en);
            status.textContent = "Filled example sentences.";
            status.style.color = "#0f3d2e";
          }} catch (e) {{
            status.textContent = "No sentences found.";
            status.style.color = "#c0392b";
          }}
        }})();
        </script>
        """,
        height=34,
        scrolling=False,
    )


def continue_pending_jobs() -> None:
    """Resume in-flight browser jobs (call once at top of Add card)."""
    if job := st.session_state.get("_lu_pending"):
        result = _run_st_javascript(_translate_js(job["text"], job["source"], job["target"]), key=job["key"])
        if _is_pending(result):
            st.info(f"Looking up {job['label'].lower()} in your browser…")
            return
        st.session_state.pop("_lu_pending", None)
        if isinstance(result, str) and result.strip():
            st.session_state[job["field"]] = result.strip()
            st.success(f"{job['label']}: {result.strip()}")
            return
        _render_inline_translation(job["text"], job["source"], job["target"], job["field"])

    if job := st.session_state.get("_sent_pending"):
        js = f"""
        {_TRANSLATE_JS}
        {_SENTENCE_JS}
        (async () => {{
          try {{ return await firstSentencePair({json.dumps(job["german"])}, {json.dumps(job["english"])}); }}
          catch (e) {{ return null; }}
        }})()
        """
        result = _run_st_javascript(js, key=job["key"])
        if _is_pending(result):
            st.info("Looking up example sentences in your browser…")
            return
        st.session_state.pop("_sent_pending", None)
        de_key = job.get("de_key", "add_sent_de")
        en_key = job.get("en_key", "add_sent_en")
        if isinstance(result, dict):
            de = str(result.get("de", "")).strip()
            en = str(result.get("en", "")).strip()
            if de and en:
                from a1.articles import normalize_example_sentences

                de, en = normalize_example_sentences(
                    job["german"],
                    job.get("english", ""),
                    de,
                    en,
                    article=job.get("article", ""),
                )
                st.session_state[de_key] = de
                st.session_state[en_key] = en
                st.success("Example sentences filled in.")
                return
        _render_inline_sentences(job["german"], job["english"])

    if job := st.session_state.get("_audio_pending"):
        _continue_audio_job(job)


def apply_translation(text: str, source: str, target: str, field: str, label: str) -> None:
    text = text.strip()
    if not text:
        st.warning("Enter a word first.")
        return

    if result := _try_server_translate(text, source, target):
        st.session_state[field] = result
        st.success(f"{label}: {result}")
        return

    n = st.session_state.get("_lu_n", 0) + 1
    st.session_state._lu_n = n
    key = f"tr_{n}"
    result = _run_st_javascript(_translate_js(text, source, target), key=key)

    if result == "__NO_JS_LIB__":
        _render_inline_translation(text, source, target, field)
        return

    if _is_pending(result):
        st.session_state["_lu_pending"] = {
            "text": text,
            "source": source,
            "target": target,
            "field": field,
            "label": label,
            "key": key,
        }
        st.info(f"Looking up {label.lower()} in your browser…")
        st.rerun()
        return

    if isinstance(result, str) and result.strip():
        st.session_state[field] = result.strip()
        st.success(f"{label}: {result.strip()}")
        return

    _render_inline_translation(text, source, target, field)


def apply_sentences(
    german: str,
    english: str = "",
    *,
    de_key: str = "add_sent_de",
    en_key: str = "add_sent_en",
    article: str = "",
) -> None:
    german = german.strip()
    if not german:
        st.warning("Enter a German word first.")
        return

    try:
        from a1.lookup import best_example_sentence

        de, en = best_example_sentence(german, english, article=article)
        st.session_state[de_key] = de
        st.session_state[en_key] = en
        st.success("Example sentences filled in.")
        return
    except Exception:
        pass

    n = st.session_state.get("_lu_n", 0) + 1
    st.session_state._lu_n = n
    key = f"sent_{n}"
    js = f"""
    {_TRANSLATE_JS}
    {_SENTENCE_JS}
    (async () => {{
      try {{ return await firstSentencePair({json.dumps(german)}, {json.dumps(english)}); }}
      catch (e) {{ return null; }}
    }})()
    """
    result = _run_st_javascript(js, key=key)

    if result == "__NO_JS_LIB__":
        _render_inline_sentences(german, english)
        return

    if _is_pending(result):
        st.session_state["_sent_pending"] = {
            "german": german,
            "english": english,
            "key": key,
            "de_key": de_key,
            "en_key": en_key,
            "article": article,
        }
        st.info("Looking up example sentences in your browser…")
        st.rerun()
        return

    if isinstance(result, dict):
        de = str(result.get("de", "")).strip()
        en = str(result.get("en", "")).strip()
        if de and en:
            from a1.articles import normalize_example_sentences

            de, en = normalize_example_sentences(german, english, de, en, article=article)
            st.session_state[de_key] = de
            st.session_state[en_key] = en
            st.success("Example sentences filled in.")
            return

    _render_inline_sentences(german, english)


_FETCH_TTS_JS = """
async function a1FetchTts(text, tl) {
  const q = encodeURIComponent(text);
  const urls = [
    "https://translate.googleapis.com/translate_tts?ie=UTF-8&client=gtx&tl=" + tl + "&q=" + q,
    "https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=" + tl + "&q=" + q,
    "https://translate.google.com/translate_tts?ie=UTF-8&tl=" + tl + "&client=dict-chromeex&q=" + q,
  ];
  for (const url of urls) {
    try {
      const resp = await fetch(url);
      if (!resp.ok) continue;
      const buf = await resp.arrayBuffer();
      if (buf.byteLength < 200) continue;
      const bytes = new Uint8Array(buf);
      let bin = "";
      for (let i = 0; i < bytes.length; i += 0x8000)
        bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
      return btoa(bin);
    } catch (e) {}
  }
  return "";
}
"""


def _continue_audio_job(job: dict[str, Any]) -> None:
    text_js = json.dumps(job["text"])
    lang_js = json.dumps(job["lang"][:2])
    js = f"""
    {_FETCH_TTS_JS}
    (async () => {{
      try {{ return await a1FetchTts({text_js}, {lang_js}); }}
      catch (e) {{ return ""; }}
    }})()
    """
    result = _run_st_javascript(js, key=job["key"])
    if _is_pending(result):
        st.info("Fetching pronunciation in your browser…")
        return
    st.session_state.pop("_audio_pending", None)
    if isinstance(result, str) and result.strip():
        try:
            data = base64.b64decode(result)
            if len(data) >= 200:
                st.session_state[job["state_key"]] = data
                st.session_state[job["ext_key"]] = ".mp3"
                st.success("Saved pronunciation from the web.")
                return
        except Exception:
            pass
    st.warning("Could not fetch audio. Use **Listen** above, then record your own.")


def fetch_audio_to_session(text: str, lang: str, *, state_key: str, ext_key: str) -> None:
    text = text.strip()
    if not text:
        st.warning("Enter the word first.")
        return

    n = st.session_state.get("_audio_n", 0) + 1
    st.session_state._audio_n = n
    key = f"aud_{n}"
    text_js = json.dumps(text)
    lang_js = json.dumps(lang[:2])
    js = f"""
    {_FETCH_TTS_JS}
    (async () => {{
      try {{ return await a1FetchTts({text_js}, {lang_js}); }}
      catch (e) {{ return ""; }}
    }})()
    """
    result = _run_st_javascript(js, key=key)

    if result == "__NO_JS_LIB__":
        st.warning("Use **Listen** to hear the word, then record below.")
        return

    if _is_pending(result):
        st.session_state["_audio_pending"] = {
            "text": text,
            "lang": lang,
            "state_key": state_key,
            "ext_key": ext_key,
            "key": key,
        }
        st.info("Fetching pronunciation in your browser…")
        st.rerun()
        return

    if isinstance(result, str) and result.strip():
        try:
            data = base64.b64decode(result)
            if len(data) >= 200:
                st.session_state[state_key] = data
                st.session_state[ext_key] = ".mp3"
                st.success("Saved pronunciation from the web.")
                return
        except Exception:
            pass
    st.warning("Could not fetch audio. Use **Listen** above, then record your own.")
