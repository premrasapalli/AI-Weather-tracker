/* global state */
let CURRENT_BUNDLE = null;
let refreshTimer = null;
const FEATURED_FALLBACK = [
  "Delhi", "Mumbai", "Bengaluru", "Hyderabad", "Chennai", "Kolkata",
  "Pune", "Jaipur", "Ahmedabad", "Lucknow", "Chandigarh", "Surat",
  "Kochi", "Bhopal", "Indore", "Patna", "Visakhapatnam", "Nashik",
];
const cities = (Array.isArray(typeof FEATURED !== 'undefined' ? FEATURED : undefined) && FEATURED.length)
  ? FEATURED : FEATURED_FALLBACK;

const $ = (id) => document.getElementById(id);

function showLoader(on = true) {
  $("loader").classList.toggle("d-none", !on);
  $("dash").classList.toggle("d-none", on);
}

function showError(msg) {
  const box = $("error-box");
  box.textContent = msg;
  box.classList.remove("d-none");
}

function hideError() { $("error-box").classList.add("d-none"); }

function tick() {
  const now = new Date().toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata", dateStyle: "full", timeStyle: "medium",
  });
  $("clock").textContent = "IST " + now;
}

async function loadCity(city) {
  showLoader(true);
  hideError();
  try {
    const res = await fetch(`/api/weather/${encodeURIComponent(city)}`);
    const data = await res.json();
    if (!data.success) throw new Error(data.error || "Unable to load weather");
    CURRENT_BUNDLE = data;
    renderDashboard(data);
    setupRefresh(data);
  } catch (err) {
    showError("Could not reach live weather data: " + err.message);
    showLoader(false);
  }
}

function setupRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(() => {
    if (CURRENT_BUNDLE && CURRENT_BUNDLE.city !== $("city-input").value.trim()) return;
    loadCity(CURRENT_BUNDLE.city);
  }, 5 * 60 * 1000);
}

function renderDashboard(b) {
  showLoader(false);
  $("city-title").textContent = b.city;
  $("city-sub").textContent = [b.state, "India"].filter(Boolean).join(" · ");

  const c = b.conditions;
  $("c-temp").textContent = Math.round(c.temp_c) + "°C";
  $("c-icon").textContent = c.icon;
  $("c-desc").textContent = [
    c.condition,
    c.is_day ? "day" : "night",
  ].join(" · ");
  $("c-feels").textContent = Math.round(c.feels_like_c) + "°C";
  $("c-humidity").textContent = c.humidity_pct;
  $("c-pressure").textContent = c.pressure_hpa ?? "--";
  $("c-wind").textContent = c.wind_kmh;
  $("c-cloud").textContent = c.cloud_pct;

  const aqi = b.aqi || {};
  $("aqi-value").textContent = aqi.aqi ?? "--";
  $("aqi-level").textContent = aqi.level || "--";
  $("aqi-level").style.background = aqi.color || "#adb5bd";
  $("aqi-value").style.color = aqi.color || "#adb5bd";
  $("aqi-drivers").textContent = (aqi.drivers || []).join(", ") || "n/a";

  const today = (b.daily || [])[0] || {};
  $("today-range").textContent = (today.tmin ?? "--") + "°C — " + (today.tmax ?? "--") + "°C";
  $("today-sunrise").textContent = fmtTime(today.sunrise) || "--";
  $("today-sunset").textContent = fmtTime(today.sunset) || "--";

  renderAlerts(b.alerts || []);
  renderHourly(b.hourly || []);
  renderDaily(b.daily || []);
  $("ai-brief").textContent = b.briefing || "AI analysis unavailable.";
  $("upd-time").textContent = "Updated " + (b.served_at ? new Date(b.served_at).toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" }) : "just now");

  $("llm-badge").textContent = b.llm_enabled
    ? "LLM-enriched answers active"
    : "AI engine mode — set LLM_API_KEY for generative answers";

  renderFeatured();
}

function fmtTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" });
}

function renderAlerts(alerts) {
  const wrap = $("alerts-wrap");
  if (!alerts.length) { wrap.hidden = true; return; }
  wrap.hidden = false;
  wrap.innerHTML = '<div class="row g-2">' + alerts.map((a) => `
    <div class="col-md-6 col-lg-4">
      <div class="alert-chip ${a.level}">
        <span>${a.level === "severe" ? "🚨" : a.level === "high" ? "⚠️" : "ℹ️"}</span>
        <div><strong>${escapeHtml(a.type)}</strong><br/><span class="small">${escapeHtml(a.message)}</span></div>
      </div>
    </div>`).join("") + "</div>";
}

function renderHourly(hours) {
  $("hourly-row").innerHTML = hours.map((h, i) => `
    <div class="hourly-item clickable" title="Ask AI about ${escapeHtml(h.day)} ${escapeHtml(h.time)}" onclick="askAboutHour('${escapeHtml(h.label || h.time)}')">
      <div class="h-time">${escapeHtml(h.day)} ${escapeHtml(h.time)}</div>
      <div class="h-temp">${Math.round(h.temp)}°</div>
      <div class="h-rain">${(h.precip_prob ?? 0) > 0 ? "💧" + h.precip_prob + "%" : "&nbsp;"}</div>
    </div>`).join("");
}

function askAboutHour(label) {
  const q = `What will the weather be like at ${label} today in ${CURRENT_BUNDLE.city}?`;
  $("chat-input").value = q;
  sendQuestion();
}

function renderDaily(days) {
  $("daily-row").innerHTML = (days || []).map((d) => {
    const dt = new Date(d.date);
    const dateStr = dt.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
    const rain = (d.precip_prob ?? 0) > 0 ? `<div class="d-rain">💧 ${d.precip_prob}%</div>` : "";
    const dayQ = dt.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });
    return `
      <div class="col-6 col-md-3 col-lg-2">
        <div class="daily-card" onclick="askAboutDay('${escapeHtml(dayQ)}')" title="Ask AI about this day">
          <div class="d-day">${dt.toLocaleDateString("en-IN", { weekday: "short" })}</div>
          <div class="d-date">${dateStr}</div>
          <div class="d-icon mt-1">${d.icon}</div>
          <div class="d-temps mt-1">${Math.round(d.tmin)}° / ${Math.round(d.tmax)}°</div>
          ${rain}
          ${d.uv != null ? `<div class="d-date">UV ${Math.round(d.uv)}</div>` : ""}
        </div>
      </div>`;
  }).join("");
}

function askAboutDay(day) {
  const q = `What is the weather forecast for ${day} in ${CURRENT_BUNDLE.city}?`;
  $("chat-input").value = q;
  sendQuestion();
}

function renderFeatured() {
  const wrap = $("featured-chips");
  if (wrap.querySelector(".featured-chip")) return;
  wrap.innerHTML = cities.map((c) =>
    `<button class="featured-chip" onclick="loadCity('${c.replace(/'/g, "")}')">${escapeHtml(c)}</button>`
  ).join("");
}

/* chat */
async function sendQuestion() {
  const input = $("chat-input");
  const q = input.value.trim();
  if (!q || !CURRENT_BUNDLE) return;
  input.value = "";
  input.disabled = false;
  const log = $("chat-log");
  log.insertAdjacentHTML("beforeend", `<div class="chat-bubble chat-user">${escapeHtml(q)}</div>`);
  const aiBubble = document.createElement("div");
  aiBubble.className = "chat-bubble chat-ai";
  aiBubble.innerHTML = `<span class="spinner-border spinner-border-sm"></span> thinking…`;
  log.appendChild(aiBubble);
  log.scrollTop = log.scrollHeight;
  try {
    const res = await fetch(`/api/ask/${encodeURIComponent(CURRENT_BUNDLE.city)}?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    aiBubble.outerHTML = `<div class="chat-bubble chat-ai">${escapeHtml(data.answer || data.error || "No answer")}</div>`;
  } catch (e) {
    aiBubble.outerHTML = `<div class="chat-bubble chat-ai">Oops — ${escapeHtml(e.message)}</div>`;
  }
  log.scrollTop = log.scrollHeight;
}

/* autocomplete with clickable options */
let debounceId = null;
let selectedFromList = false;
const $suggest = () => $("suggestions");

function renderSuggestions(results) {
  const box = $suggest();
  if (!results.length) { box.classList.add("d-none"); box.innerHTML = ""; return; }
  box.classList.remove("d-none");
  box.innerHTML = results.map((r, i) => `
    <div class="suggest-item" data-i="${i}">
      <span class="s-ico">📍</span>
      <div><div class="s-name">${escapeHtml(r.name)}</div>
      <div class="s-sub">${escapeHtml([r.state, r.country_code].filter(Boolean).join(" · "))}</div></div>
    </div>`).join("");
  box.querySelectorAll(".suggest-item").forEach((el) => {
    el.addEventListener("click", () => {
      const r = results[parseInt(el.dataset.i, 10)];
      selectedFromList = true;
      $("city-input").value = r.name;
      hideSuggestions();
      loadCity(r.name);
    });
  });
}

function hideSuggestions() { $suggest().classList.add("d-none"); $suggest().innerHTML = ""; }

$("city-input").addEventListener("input", (e) => {
  clearTimeout(debounceId);
  const q = e.target.value.trim();
  selectedFromList = false;
  if (q.length < 2) { hideSuggestions(); return; }
  debounceId = setTimeout(async () => {
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      renderSuggestions(data.success ? data.results : []);
    } catch (_) { hideSuggestions(); }
  }, 300);
});
document.addEventListener("click", (e) => {
  if (!e.target.closest("#suggestions") && !e.target.closest("#city-input")) hideSuggestions();
});

$("search-btn").addEventListener("click", () => {
  hideSuggestions();
  const v = $("city-input").value.trim();
  if (v) loadCity(v);
});
$("city-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    hideSuggestions();
    const v = e.target.value.trim();
    if (v) loadCity(v);
  }
});
$("refresh-btn").addEventListener("click", () => CURRENT_BUNDLE && loadCity(CURRENT_BUNDLE.city));
$("chat-send").addEventListener("click", sendQuestion);
$("chat-input").addEventListener("keydown", (e) => e.key === "Enter" && sendQuestion());

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
}

/* boot */
document.addEventListener("DOMContentLoaded", () => {
  tick();
  setInterval(tick, 1000);
  loadCity(INITIAL_CITY);
});