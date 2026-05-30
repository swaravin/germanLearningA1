const NOUN_ARTICLES = {
  Haus: "das", Hund: "der", Katze: "die", Schiff: "das", Ort: "der", Kirche: "die", Fahrrad: "das",
};

const CEFR_STORAGE_KEY = "de_cefr_level";
const COMFORT_WEIGHTED_KEY = "de_comfort_weighted";

const COMFORT_FILTERS = [
  ["all", "All words"],
  ["unrated", "Not rated yet"],
  ["weak", "Need practice (1–2 or unrated)"],
  ["1", "1 — Still learning"],
  ["2", "2 — Shaky"],
  ["3", "3 — OK"],
  ["4", "4 — Good"],
  ["5", "5 — Comfortable"],
];

const COMFORT_LABELS = {
  1: "Still learning",
  2: "Shaky",
  3: "OK",
  4: "Good",
  5: "Comfortable",
};

const MIN_COMFORT = 1;
const MAX_COMFORT = 5;

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
  comfortFilter: "all",
  comfortWeighted: true,
  comfortData: { version: 1, words: {} },
  cardFrontHtml: "",
  cardBackHtml: "",
  flipAnimating: false,
};

function comfortStorageKey(levelId = state.cefrLevel) {
  return `de_comfort_${levelId}`;
}

function comfortFilterStorageKey(levelId = state.cefrLevel) {
  return `de_comfort_filter_${levelId}`;
}

function normalizeComfortFilter(filterKey) {
  const valid = new Set(COMFORT_FILTERS.map(([k]) => k));
  if (filterKey == null || filterKey === true || filterKey === false) return "all";
  let text = String(filterKey).trim();
  if (text.includes("(")) text = text.split("(", 1)[0].trim();
  if (valid.has(text)) return text;
  const lower = text.toLowerCase();
  for (const [key, label] of COMFORT_FILTERS) {
    if (lower === label.toLowerCase()) return key;
  }
  return "all";
}

function comfortFilterLabel(filterKey) {
  const key = normalizeComfortFilter(filterKey);
  const match = COMFORT_FILTERS.find(([k]) => k === key);
  return match ? match[1] : key;
}

function loadComfortData() {
  try {
    const raw = localStorage.getItem(comfortStorageKey());
    if (!raw) {
      state.comfortData = { version: 1, words: {} };
      return;
    }
    const data = JSON.parse(raw);
    state.comfortData =
      data && typeof data === "object" ? { version: 1, words: data.words || {} } : { version: 1, words: {} };
  } catch (_) {
    state.comfortData = { version: 1, words: {} };
  }
}

function saveComfortData() {
  localStorage.setItem(comfortStorageKey(), JSON.stringify(state.comfortData));
}

function getComfortLevel(wordId) {
  const entry = state.comfortData.words[String(wordId)];
  if (!entry) return null;
  const level = Number(entry.level);
  if (!Number.isFinite(level)) return null;
  return Math.max(MIN_COMFORT, Math.min(MAX_COMFORT, level));
}

function effectiveComfortLevel(wordId) {
  return getComfortLevel(wordId) ?? MIN_COMFORT;
}

function setComfortLevel(wordId, level) {
  const clamped = Math.max(MIN_COMFORT, Math.min(MAX_COMFORT, Number(level)));
  const key = String(wordId);
  const prev = state.comfortData.words[key] || {};
  state.comfortData.words[key] = {
    level: clamped,
    seen: Number(prev.seen || 0) + 1,
    updated: new Date().toISOString(),
  };
  saveComfortData();
  return clamped;
}

function weightForWord(wordId) {
  const level = effectiveComfortLevel(wordId);
  return MAX_COMFORT + MIN_COMFORT - level;
}

function filterByComfort(list, filterKey) {
  const key = normalizeComfortFilter(filterKey);
  if (key === "all") return [...list];
  return list.filter((w) => {
    const level = getComfortLevel(w.id);
    if (key === "unrated") return level == null;
    if (key === "weak") return level == null || level <= 2;
    if (["1", "2", "3", "4", "5"].includes(key)) return level === Number(key);
    return true;
  });
}

function weightedShuffle(list) {
  if (list.length <= 1) return [...list];
  const remaining = [...list];
  const ordered = [];
  while (remaining.length) {
    const weights = remaining.map((w) => weightForWord(w.id));
    const pick = weightedChoice(remaining, weights);
    ordered.push(pick);
    remaining.splice(remaining.indexOf(pick), 1);
  }
  return ordered;
}

function weightedChoice(items, weights) {
  const total = weights.reduce((a, b) => a + b, 0);
  let roll = Math.random() * total;
  for (let i = 0; i < items.length; i++) {
    roll -= weights[i];
    if (roll <= 0) return items[i];
  }
  return items[items.length - 1];
}

function explainEmptyComfortFilter(sectionList, filteredCount) {
  const key = normalizeComfortFilter(state.comfortFilter);
  if (key === "all") {
    if (!sectionList.length) {
      return state.section === "all"
        ? "No words in this level."
        : `No words in section "${state.section}". Try All sections.`;
    }
    return "No words match your filters.";
  }

  const inLevel = filterByComfort(state.words, key).length;
  const inSection = filterByComfort(sectionList, key).length;

  if (inSection === 0 && inLevel > 0 && state.section !== "all") {
    return `You have ${inLevel} word(s) at this comfort level in other sections. Set Section to All sections, or rate cards in "${state.section}".`;
  }

  if (["1", "2", "3", "4", "5"].includes(key) && inLevel === 0) {
    return `No cards rated ${comfortFilterLabel(key)} yet. Set Practice by comfort to All words, flip cards, and tap 1–5 below each card.`;
  }

  if (key === "unrated" && inLevel === 0) {
    return "Every word in this level is already rated. Pick a comfort level (1–5) instead.";
  }

  if (key === "weak" && inLevel === 0) {
    return "No words need practice at this level (all rated 3–5). Try All words or a specific level.";
  }

  return "No words match this comfort filter. Try All sections or All words, then rate cards with 1–5.";
}

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
  const weightedSaved = localStorage.getItem(COMFORT_WEIGHTED_KEY);
  state.comfortWeighted = weightedSaved == null ? true : weightedSaved === "true";
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

function fillComfortSelect() {
  const sel = document.getElementById("comfort-filter");
  if (!sel) return;
  sel.innerHTML = "";
  for (const [key, label] of COMFORT_FILTERS) {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = label;
    sel.appendChild(opt);
  }
  sel.value = normalizeComfortFilter(state.comfortFilter);
}

function loadComfortPreferences() {
  loadComfortData();
  const savedFilter = localStorage.getItem(comfortFilterStorageKey());
  state.comfortFilter = normalizeComfortFilter(savedFilter || "all");
  fillComfortSelect();
  const weightedEl = document.getElementById("comfort-weighted");
  if (weightedEl) weightedEl.checked = state.comfortWeighted;
}

async function loadWords() {
  const baseUrl = `./data/levels/${state.cefrLevel}/vocabulary.json`;
  const customUrl = `./data/levels/${state.cefrLevel}/custom_vocabulary.json`;
  const [baseResp, customResp] = await Promise.all([fetch(baseUrl), fetch(customUrl)]);
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
  loadComfortPreferences();
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

function sectionFilteredWords() {
  if (state.section === "all") return state.words;
  return state.words.filter((w) => w.section === state.section);
}

function rebuildDeck() {
  let list = sectionFilteredWords();
  list = filterByComfort(list, state.comfortFilter);
  if (state.comfortWeighted) {
    state.deck = weightedShuffle(list);
  } else {
    state.deck = [...list].sort(() => Math.random() - 0.5);
  }
  state.index = 0;
  state.flipped = false;
  renderCard();
}

function currentWord() {
  return state.deck[state.index];
}

function updateComfortUI(word) {
  const panel = document.getElementById("comfort-panel");
  const labelEl = document.getElementById("comfort-label");
  const hintEl = document.getElementById("empty-deck-hint");
  if (!panel || !labelEl) return;

  if (!word) {
    panel.classList.add("hidden");
    if (hintEl) {
      hintEl.classList.remove("hidden");
      hintEl.textContent = explainEmptyComfortFilter(sectionFilteredWords(), 0);
    }
    return;
  }

  panel.classList.remove("hidden");
  if (hintEl) hintEl.classList.add("hidden");

  const saved = getComfortLevel(word.id);
  const label = saved ? COMFORT_LABELS[saved] : "Not rated yet";
  const stars = "★".repeat(effectiveComfortLevel(word.id)) + "☆".repeat(5 - effectiveComfortLevel(word.id));
  labelEl.textContent = `Comfort: ${label} · ${stars}`;

  document.querySelectorAll(".comfort-btn").forEach((btn) => {
    const level = Number(btn.dataset.level);
    btn.classList.toggle("active", saved === level);
  });
}

function resetCardFlipAnimation() {
  const card = document.getElementById("flashcard");
  if (!card) return;
  card.classList.remove("flip-out", "flip-in-start", "flip-in-end");
  card.style.transition = "";
  card.style.transform = "";
  state.flipAnimating = false;
}

function waitCardTransition(card) {
  return new Promise((resolve) => {
    const onEnd = (event) => {
      if (event.target !== card || event.propertyName !== "transform") return;
      card.removeEventListener("transitionend", onEnd);
      resolve();
    };
    card.addEventListener("transitionend", onEnd);
  });
}

function buildCardSides(w) {
  const sectionTag = w.section
    ? `<div class="section-tag">${w.section.replace(/^\d+\.\s*/, "")}</div>`
    : "";

  if (state.front === "english") {
    return {
      front: `${sectionTag}<div class="english">${englishShort(w.english)}</div>`,
      back: `<div class="german">${germanDisplay(w)}</div>`,
    };
  }
  if (state.front === "both") {
    return {
      front: `${sectionTag}<div class="german">${germanDisplay(w)}</div><div class="english">${englishShort(w.english)}</div>`,
      back: `<div class="sentence">${w.sentence_de || ""}</div><div class="sentence">${w.sentence_en || ""}</div>`,
    };
  }
  return {
    front: `${sectionTag}<div class="german">${germanDisplay(w)}</div>`,
    back: `<div class="english">${englishShort(w.english)}</div>`,
  };
}

function renderCardFace() {
  const faceEl = document.getElementById("card-face");
  if (!faceEl) return;
  faceEl.innerHTML = state.flipped ? state.cardBackHtml : state.cardFrontHtml;
}

function renderCard() {
  const card = document.getElementById("flashcard");
  const w = currentWord();
  updateComfortUI(w);
  if (!w) {
    document.getElementById("progress").textContent = "No words match your filters.";
    document.getElementById("progress-fill").style.width = "0%";
    card.classList.add("hidden");
    return;
  }
  card.classList.remove("hidden");
  resetCardFlipAnimation();
  state.flipped = false;

  const pct = state.deck.length ? ((state.index + 1) / state.deck.length) * 100 : 0;
  document.getElementById("progress-fill").style.width = `${pct}%`;
  const meta = currentLevelMeta();
  document.getElementById("progress").textContent =
    `${meta.label} · Card ${state.index + 1} / ${state.deck.length} · ${w.section || ""}`;

  const sides = buildCardSides(w);
  state.cardFrontHtml = sides.front;
  state.cardBackHtml = sides.back;
  renderCardFace();

  const sent = document.getElementById("card-sentence");
  if (state.front !== "both") {
    sent.innerHTML = w.sentence_de
      ? `<div class="sentence">${w.sentence_de}</div><div class="sentence">${w.sentence_en || ""}</div>`
      : "";
  } else {
    sent.innerHTML = "";
  }
}

async function flipCard() {
  if (state.flipAnimating) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduceMotion) {
    state.flipped = !state.flipped;
    renderCardFace();
    return;
  }

  const card = document.getElementById("flashcard");
  state.flipAnimating = true;
  card.classList.remove("flip-in-start", "flip-in-end", "flip-out");
  card.classList.add("flip-out");
  await waitCardTransition(card);

  state.flipped = !state.flipped;
  renderCardFace();

  card.classList.remove("flip-out");
  card.classList.add("flip-in-start");
  card.offsetHeight;
  card.classList.remove("flip-in-start");
  card.classList.add("flip-in-end");
  await waitCardTransition(card);

  card.classList.remove("flip-in-end");
  state.flipAnimating = false;
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
  document.getElementById("comfort-filter").addEventListener("change", (e) => {
    state.comfortFilter = normalizeComfortFilter(e.target.value);
    localStorage.setItem(comfortFilterStorageKey(), state.comfortFilter);
    rebuildDeck();
  });
  document.getElementById("comfort-weighted").addEventListener("change", (e) => {
    state.comfortWeighted = e.target.checked;
    localStorage.setItem(COMFORT_WEIGHTED_KEY, String(state.comfortWeighted));
    rebuildDeck();
  });
  document.getElementById("comfort-buttons").addEventListener("click", (e) => {
    const btn = e.target.closest(".comfort-btn");
    if (!btn) return;
    const w = currentWord();
    if (!w) return;
    e.stopPropagation();
    setComfortLevel(w.id, Number(btn.dataset.level));
    updateComfortUI(w);
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
  fillComfortSelect();
  bindEvents();
  await loadLevelManifest();
  await loadWords();
}

init();
