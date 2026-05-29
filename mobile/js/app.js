const NOUN_ARTICLES = {
  Haus: "das", Hund: "der", Katze: "die", Schiff: "das", Ort: "der", Kirche: "die", Fahrrad: "das",
};

const CEFR_STORAGE_KEY = "de_cefr_level";

const state = {
  levels: [],
  cefrLevel: "a1",
  words: [],
  deck: [],
  index: 0,
  flipped: false,
  front: "german",
  section: "all",
  sections: [],
};

function articleFor(word) {
  if (word.article && word.article !== "—") return word.article;
  const lemma = (word.german || "").trim().split(/\s+/)[0];
  const titled = lemma.charAt(0).toUpperCase() + lemma.slice(1);
  return NOUN_ARTICLES[lemma] || NOUN_ARTICLES[titled] || "";
}

function germanDisplay(word) {
  const g = (word.german || "").trim();
  const art = articleFor(word);
  if (!art) return g;
  const lemma = g.split(/\s+/)[0];
  const rest = g.slice(lemma.length).trim();
  return `<span class="article">${art}</span> ${lemma}${rest ? " " + rest : ""}`;
}

function englishShort(en) {
  return (en || "").split(/[,;(/]/)[0].trim();
}

function speak(text, lang) {
  if (!text || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  u.rate = lang.startsWith("de") ? 0.85 : 1;
  window.speechSynthesis.speak(u);
}

function currentLevelMeta() {
  return state.levels.find((l) => l.id === state.cefrLevel) || state.levels[0] || { title: "German Learn", label: "A1" };
}

function updateHeader() {
  const meta = currentLevelMeta();
  document.getElementById("app-title").textContent = `🇩🇪 ${meta.title || "German Learn"}`;
  document.title = meta.title || "German Learn";
}

async function loadLevelManifest() {
  const resp = await fetch("./data/levels.json");
  const data = await resp.json();
  state.levels = (data.levels || []).filter((l) => l.id);
  const saved = localStorage.getItem(CEFR_STORAGE_KEY);
  if (saved && state.levels.some((l) => l.id === saved)) {
    state.cefrLevel = saved;
  } else {
    state.cefrLevel = data.default || state.levels[0]?.id || "a1";
  }
  fillLevelSelect();
  updateHeader();
}

function fillLevelSelect() {
  const sel = document.getElementById("cefr-level");
  if (!sel) return;
  sel.innerHTML = "";
  for (const lv of state.levels) {
    const opt = document.createElement("option");
    opt.value = lv.id;
    const sub = lv.subtitle ? ` — ${lv.subtitle}` : "";
    opt.textContent = `${lv.label}${sub}`;
    sel.appendChild(opt);
  }
  sel.value = state.cefrLevel;
}

async function loadWords() {
  const baseUrl = `./data/levels/${state.cefrLevel}/vocabulary.json`;
  const customUrl = `./data/levels/${state.cefrLevel}/custom_vocabulary.json`;
  const [baseResp, customResp] = await Promise.all([
    fetch(baseUrl),
    fetch(customUrl),
  ]);
  if (!baseResp.ok) {
    document.getElementById("progress").textContent = `No word list for ${state.cefrLevel.toUpperCase()}.`;
    state.words = [];
    state.deck = [];
    return;
  }
  const base = (await baseResp.json()).words || [];
  let custom = [];
  try {
    if (customResp.ok) custom = (await customResp.json()).words || [];
  } catch (_) {}
  const byId = new Map();
  for (const w of base) byId.set(w.id, w);
  for (const w of custom) byId.set(w.id, w);
  state.words = [...byId.values()];
  state.sections = ["all", ...new Set(state.words.map((w) => w.section).filter(Boolean))];
  rebuildDeck();
  fillSectionSelect();
}

function fillSectionSelect() {
  const sel = document.getElementById("section-filter");
  sel.innerHTML = "";
  for (const s of state.sections) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s === "all" ? "All sections" : s;
    sel.appendChild(opt);
  }
  sel.value = state.section;
}

function rebuildDeck() {
  let list = state.words;
  if (state.section !== "all") {
    list = list.filter((w) => w.section === state.section);
  }
  state.deck = [...list].sort(() => Math.random() - 0.5);
  state.index = 0;
  state.flipped = false;
  renderCard();
}

function currentWord() {
  return state.deck[state.index];
}

function renderCard() {
  const card = document.getElementById("flashcard");
  const w = currentWord();
  if (!w) {
    document.getElementById("progress").textContent = "No words in this section.";
    document.getElementById("progress-fill").style.width = "0%";
    card.classList.add("hidden");
    return;
  }
  card.classList.remove("hidden");
  card.classList.remove("flipped");
  state.flipped = false;

  const pct = state.deck.length ? ((state.index + 1) / state.deck.length) * 100 : 0;
  document.getElementById("progress-fill").style.width = `${pct}%`;
  const meta = currentLevelMeta();
  document.getElementById("progress").textContent =
    `${meta.label} · Card ${state.index + 1} / ${state.deck.length} · ${w.section || ""}`;

  const frontEl = document.getElementById("card-front");
  const backEl = document.getElementById("card-back");
  const sectionTag = w.section
    ? `<div class="section-tag">${w.section.replace(/^\d+\.\s*/, "")}</div>`
    : "";

  if (state.front === "english") {
    frontEl.innerHTML = `${sectionTag}<div class="english">${englishShort(w.english)}</div>`;
    backEl.innerHTML = `<div class="german">${germanDisplay(w)}</div>`;
  } else if (state.front === "both") {
    frontEl.innerHTML = `${sectionTag}<div class="german">${germanDisplay(w)}</div><div class="english">${englishShort(w.english)}</div>`;
    backEl.innerHTML = `<div class="sentence">${w.sentence_de || ""}</div><div class="sentence">${w.sentence_en || ""}</div>`;
  } else {
    frontEl.innerHTML = `${sectionTag}<div class="german">${germanDisplay(w)}</div>`;
    backEl.innerHTML = `<div class="english">${englishShort(w.english)}</div>`;
  }

  const sent = document.getElementById("card-sentence");
  if (state.front !== "both") {
    sent.innerHTML = w.sentence_de
      ? `<div class="sentence">${w.sentence_de}</div><div class="sentence">${w.sentence_en || ""}</div>`
      : "";
  } else {
    sent.innerHTML = "";
  }
}

function flipCard() {
  state.flipped = !state.flipped;
  document.getElementById("flashcard").classList.toggle("flipped", state.flipped);
}

function nextCard() {
  if (!state.deck.length) return;
  state.index = (state.index + 1) % state.deck.length;
  state.flipped = false;
  renderCard();
}

function prevCard() {
  if (!state.deck.length) return;
  state.index = (state.index - 1 + state.deck.length) % state.deck.length;
  state.flipped = false;
  renderCard();
}

function renderBrowse(query = "") {
  const list = document.getElementById("word-list");
  const q = query.trim().toLowerCase();
  const items = state.words.filter((w) => {
    if (!q) return true;
    return (
      (w.german || "").toLowerCase().includes(q) ||
      (w.english || "").toLowerCase().includes(q)
    );
  });
  list.innerHTML = items
    .slice(0, 200)
    .map(
      (w) =>
        `<li><div class="de">${germanDisplay(w)}</div><div class="en">${englishShort(w.english)}</div></li>`
    )
    .join("");
  if (items.length > 200) {
    list.innerHTML += `<li>…and ${items.length - 200} more (refine search)</li>`;
  }
}

function showTab(name) {
  document.getElementById("flash-view").classList.toggle("hidden", name !== "flash");
  document.getElementById("browse-view").classList.toggle("hidden", name !== "browse");
  document.getElementById("tab-flash").classList.toggle("active", name === "flash");
  document.getElementById("tab-browse").classList.toggle("active", name === "browse");
  if (name === "browse") renderBrowse(document.getElementById("search").value);
}

function isStandalone() {
  return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone;
}

function setupInstallHint() {
  const hint = document.getElementById("install-hint");
  if (isStandalone()) {
    hint.classList.add("hidden");
    return;
  }
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
  hint.innerHTML = isIOS
    ? "<strong>Install on iPhone:</strong> tap <strong>Share</strong> (↑) in Safari, then <strong>Add to Home Screen</strong>."
    : "<strong>Install:</strong> use your browser menu → <strong>Add to Home Screen</strong> or <strong>Install app</strong>.";
}

async function onCefrChange(levelId) {
  state.cefrLevel = levelId;
  localStorage.setItem(CEFR_STORAGE_KEY, levelId);
  state.section = "all";
  fillLevelSelect();
  updateHeader();
  await loadWords();
}

function bindEvents() {
  document.getElementById("flashcard").addEventListener("click", flipCard);
  document.getElementById("btn-prev").addEventListener("click", prevCard);
  document.getElementById("btn-next").addEventListener("click", nextCard);
  document.getElementById("btn-shuffle").addEventListener("click", rebuildDeck);
  document.getElementById("btn-speak-de").addEventListener("click", () => {
    const w = currentWord();
    if (w) speak(germanDisplay(w).replace(/<[^>]+>/g, ""), "de-DE");
  });
  document.getElementById("btn-speak-en").addEventListener("click", () => {
    const w = currentWord();
    if (w) speak(englishShort(w.english), "en-US");
  });
  document.getElementById("front-mode").addEventListener("change", (e) => {
    state.front = e.target.value;
    renderCard();
  });
  document.getElementById("section-filter").addEventListener("change", (e) => {
    state.section = e.target.value;
    rebuildDeck();
  });
  document.getElementById("cefr-level").addEventListener("change", (e) => {
    onCefrChange(e.target.value);
  });
  document.getElementById("tab-flash").addEventListener("click", () => showTab("flash"));
  document.getElementById("tab-browse").addEventListener("click", () => showTab("browse"));
  document.getElementById("search").addEventListener("input", (e) => renderBrowse(e.target.value));
}

async function init() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./sw.js").catch(() => {});
  }
  setupInstallHint();
  bindEvents();
  await loadLevelManifest();
  await loadWords();
}

init();
