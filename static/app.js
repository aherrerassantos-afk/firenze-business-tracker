/**
 * app.js — Firenze Business Tracker
 * Logica frontend: fetch dati, tabella, filtri, grafici
 */

// ── Stato globale ──────────────────────────────────────────────────────────
const state = {
  imprese: [],
  filtrate: [],
  paginaCorrente: 1,
  perPagina: 20,
  sortCol: "data_iscrizione",
  sortDir: "desc",
};

// ── Utility ────────────────────────────────────────────────────────────────

function formatData(dateStr) {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("it-IT", {
      day: "2-digit", month: "2-digit", year: "numeric",
    });
  } catch { return dateStr; }
}

function formatDataBreve(dateStr) {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("it-IT", { day: "2-digit", month: "short" });
  } catch { return dateStr; }
}

function oggi() {
  return new Date().toISOString().split("T")[0];
}

function showToast(msg, tipo = "info") {
  let toast = document.getElementById("toastEl");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toastEl";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = `toast ${tipo}`;
  requestAnimationFrame(() => {
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3500);
  });
}

function animaNumero(el, target, durata = 800) {
  const start = 0;
  const startTime = performance.now();
  function step(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / durata, 1);
    const ease = 1 - Math.pow(1 - progress, 3); // easeOutCubic
    el.textContent = Math.round(start + (target - start) * ease);
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── Caricamento Dati ───────────────────────────────────────────────────────

async function caricaDati() {
  const giorni = document.getElementById("filtroGiorni").value;
  const loadingEl = document.getElementById("loadingOverlay");
  const tableEl = document.getElementById("dataTable");

  loadingEl.style.display = "flex";
  tableEl.style.opacity = "0.3";

  try {
    const [resImprese, resStats] = await Promise.all([
      fetch(`/api/imprese?limit=500&giorni=${giorni}`),
      fetch("/api/stats"),
    ]);

    const datiImprese = await resImprese.json();
    const datiStats = await resStats.json();

    if (datiImprese.success) {
      state.imprese = datiImprese.imprese || [];
      aggiornaHeaderStatus("ok", datiImprese.metadata);
      aggiornaStats(datiImprese.imprese, datiStats);
      popolaFiltroComuni(datiImprese.imprese);
      filtraTabella();
    }

    if (datiStats.success) {
      renderGrafici(datiStats);
      if (datiStats.metadata?.ultimo_aggiornamento) {
        document.getElementById("footerUpdate").textContent =
          `Ultimo aggiornamento: ${datiStats.metadata.ultimo_aggiornamento}`;
      }
    }
  } catch (err) {
    console.error("Errore caricamento:", err);
    aggiornaHeaderStatus("error", null);
    showToast("❌ Errore connessione al server", "error");
  } finally {
    loadingEl.style.display = "none";
    tableEl.style.opacity = "1";
  }
}

// ── Header Status ──────────────────────────────────────────────────────────

function aggiornaHeaderStatus(stato, metadata) {
  const dot = document.getElementById("statusDot");
  const text = document.getElementById("statusText");
  dot.className = "status-dot " + stato;

  if (stato === "ok" && metadata) {
    const data = metadata.ultimo_aggiornamento || "—";
    text.textContent = `Aggiornato: ${data.split(" ")[0]}`;
  } else if (stato === "error") {
    text.textContent = "Errore connessione";
  } else {
    text.textContent = "Caricamento...";
    dot.className = "status-dot loading";
  }
}

// ── Stats Cards ────────────────────────────────────────────────────────────

function aggiornaStats(imprese, stats) {
  // Totale
  const elTotale = document.getElementById("numTotale");
  animaNumero(elTotale, imprese.length);

  // Oggi
  const oggiStr = oggi();
  const numOggi = imprese.filter(i => i.data_iscrizione === oggiStr).length;
  animaNumero(document.getElementById("numOggi"), numOggi);
  document.getElementById("dataOggi").textContent =
    new Date().toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long" });

  // Comuni
  const comuniUnici = new Set(imprese.map(i => i.comune).filter(Boolean));
  animaNumero(document.getElementById("numComuni"), comuniUnici.size);

  // Settori
  const settoriUnici = new Set(imprese.map(i => i.codice_ateco).filter(Boolean));
  animaNumero(document.getElementById("numSettori"), settoriUnici.size);
}

// ── Filtro Comuni (select) ─────────────────────────────────────────────────

function popolaFiltroComuni(imprese) {
  const select = document.getElementById("filtroComune");
  const valoreCorrente = select.value;
  const comuni = [...new Set(imprese.map(i => i.comune).filter(Boolean))].sort();

  select.innerHTML = '<option value="">Tutti i comuni</option>';
  comuni.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.toLowerCase();
    opt.textContent = c;
    select.appendChild(opt);
  });

  if (valoreCorrente) select.value = valoreCorrente;
}

// ── Filtro e Ricerca ───────────────────────────────────────────────────────

function filtraTabella() {
  const search = document.getElementById("searchInput").value.toLowerCase().trim();
  const comune = document.getElementById("filtroComune").value.toLowerCase();
  const clearBtn = document.getElementById("searchClear");

  clearBtn.style.display = search ? "block" : "none";

  state.filtrate = state.imprese.filter(imp => {
    const matchSearch = !search || [
      imp.denominazione, imp.indirizzo, imp.desc_ateco, imp.comune, imp.codice_ateco,
    ].some(v => v && v.toLowerCase().includes(search));

    const matchComune = !comune || (imp.comune || "").toLowerCase().includes(comune);

    return matchSearch && matchComune;
  });

  ordinaTabella();
}

function clearSearch() {
  document.getElementById("searchInput").value = "";
  document.getElementById("searchClear").style.display = "none";
  filtraTabella();
}

// ── Ordinamento ────────────────────────────────────────────────────────────

function sortBy(col) {
  if (state.sortCol === col) {
    state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
  } else {
    state.sortCol = col;
    state.sortDir = col === "data_iscrizione" ? "desc" : "asc";
  }
  // Aggiorna frecce
  document.querySelectorAll(".sort-arrow").forEach(el => el.classList.remove("active"));
  const activeArrow = document.querySelector(`.sort-arrow[data-col="${col}"]`);
  if (activeArrow) {
    activeArrow.classList.add("active");
    activeArrow.textContent = state.sortDir === "asc" ? "↑" : "↓";
  }

  ordinaTabella();
}

function ordinaTabella() {
  const ordine = document.getElementById("filtroOrdine").value;

  let sorted = [...state.filtrate];

  // Usa select ordine solo se non è stato cliccato un header
  if (ordine && ordine !== "custom") {
    switch (ordine) {
      case "data_desc": sorted.sort((a, b) => (b.data_iscrizione || "").localeCompare(a.data_iscrizione || "")); break;
      case "data_asc":  sorted.sort((a, b) => (a.data_iscrizione || "").localeCompare(b.data_iscrizione || "")); break;
      case "nome_asc":  sorted.sort((a, b) => (a.denominazione || "").localeCompare(b.denominazione || "")); break;
      case "nome_desc": sorted.sort((a, b) => (b.denominazione || "").localeCompare(a.denominazione || "")); break;
      case "comune":    sorted.sort((a, b) => (a.comune || "").localeCompare(b.comune || "")); break;
    }
  } else {
    sorted.sort((a, b) => {
      const va = (a[state.sortCol] || "").toString();
      const vb = (b[state.sortCol] || "").toString();
      return state.sortDir === "asc" ? va.localeCompare(vb) : vb.localeCompare(va);
    });
  }

  state.filtrate = sorted;
  state.paginaCorrente = 1;
  renderTabella();
}

// ── Render Tabella ─────────────────────────────────────────────────────────

function renderTabella() {
  const tbody = document.getElementById("tableBody");
  const emptyState = document.getElementById("emptyState");
  const countEl = document.getElementById("risultatiCount");

  const totale = state.filtrate.length;
  countEl.textContent = `${totale} result${totale !== 1 ? "i" : "o"}`;

  if (totale === 0) {
    emptyState.style.display = "block";
    tbody.innerHTML = "";
    document.getElementById("pagination").style.display = "none";
    return;
  }

  emptyState.style.display = "none";

  // Paginazione
  const totalePagine = Math.ceil(totale / state.perPagina);
  const inizio = (state.paginaCorrente - 1) * state.perPagina;
  const fine = Math.min(inizio + state.perPagina, totale);
  const paginaItems = state.filtrate.slice(inizio, fine);

  // Aggiorna controlli paginazione
  const paginationEl = document.getElementById("pagination");
  paginationEl.style.display = totalePagine > 1 ? "flex" : "none";
  document.getElementById("pageInfo").textContent =
    `Pagina ${state.paginaCorrente} di ${totalePagine} (${inizio + 1}–${fine} di ${totale})`;
  document.getElementById("btnPrevPage").disabled = state.paginaCorrente <= 1;
  document.getElementById("btnNextPage").disabled = state.paginaCorrente >= totalePagine;

  // Render righe
  const html = paginaItems.map((imp, idx) => {
    const delay = idx * 20;
    const dataFormattata = formatData(imp.data_iscrizione);
    const isOggi = imp.data_iscrizione === oggi();

    return `
    <tr style="animation-delay: ${delay}ms">
      <td>
        <div class="date-badge" title="${imp.data_iscrizione || ""}">
          ${dataFormattata}
          ${isOggi ? ' <span style="color:var(--orange-400);font-size:10px">●</span>' : ""}
        </div>
      </td>
      <td>
        <div class="nome-cell">
          ${escapeHTML(imp.denominazione || "N/D")}
          ${imp.partita_iva ? `<small>P.IVA: ${escapeHTML(imp.partita_iva)}</small>` : ""}
        </div>
      </td>
      <td>
        <span class="comune-pill">📍 ${escapeHTML(imp.comune || "—")}</span>
      </td>
      <td style="font-size:13px;color:var(--text-secondary)">
        ${escapeHTML(imp.indirizzo || "—")}
      </td>
      <td>
        ${imp.codice_ateco ? `<div class="ateco-badge">${escapeHTML(imp.codice_ateco)}</div>` : ""}
        <div class="ateco-desc">${escapeHTML(imp.desc_ateco || "—")}</div>
      </td>
      <td>
        <span class="forma-text">${escapeHTML(imp.forma_giuridica || "—")}</span>
      </td>
      <td>
        <span class="stato-badge stato-attiva">${escapeHTML(imp.stato || "Attiva")}</span>
      </td>
    </tr>`;
  }).join("");

  tbody.innerHTML = html;
}

function escapeHTML(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function changePage(delta) {
  const totale = state.filtrate.length;
  const totalePagine = Math.ceil(totale / state.perPagina);
  state.paginaCorrente = Math.max(1, Math.min(totalePagine, state.paginaCorrente + delta));
  renderTabella();
  document.querySelector(".table-container").scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Grafici ────────────────────────────────────────────────────────────────

function renderGrafici(stats) {
  renderBarChart("chartComuni", stats.per_comune, "var(--grad-blue)");
  renderBarChart("chartSettori", stats.top_settori, "var(--grad-green)");
  renderTrendChart("chartTrend", stats.trend_giornaliero || []);
}

function renderBarChart(containerId, data, gradient) {
  const container = document.getElementById(containerId);
  if (!container || !data) return;

  const entries = Object.entries(data).slice(0, 8);
  const maxVal = Math.max(...entries.map(([, v]) => v), 1);

  container.innerHTML = entries.map(([label, val]) => `
    <div class="bar-row">
      <span class="bar-label" title="${escapeHTML(label)}">${escapeHTML(label)}</span>
      <div class="bar-track">
        <div class="bar-fill" style="width: ${(val / maxVal * 100).toFixed(1)}%; background: ${gradient}"></div>
      </div>
      <span class="bar-value">${val}</span>
    </div>
  `).join("");
}

function renderTrendChart(containerId, trend) {
  const container = document.getElementById(containerId);
  if (!container || !trend.length) return;

  const maxVal = Math.max(...trend.map(([, v]) => v), 1);
  const ultimi14 = trend.slice(-14);

  container.innerHTML = ultimi14.map(([data, val]) => {
    const altezzaPercent = Math.max((val / maxVal * 100), 4);
    const label = formatDataBreve(data);
    return `
      <div class="trend-col">
        <div class="trend-bar"
             data-value="${val} imprese"
             style="height: ${altezzaPercent}%"
             title="${data}: ${val} nuove imprese"
        ></div>
        <span class="trend-label">${label}</span>
      </div>
    `;
  }).join("");
}

// ── Aggiornamento Manuale ──────────────────────────────────────────────────

async function aggiornaManuale() {
  const btn = document.getElementById("btnRefresh");
  const icona = btn.querySelector("svg");

  btn.disabled = true;
  icona.classList.add("spin");
  showToast("🔄 Aggiornamento in corso...", "info");
  aggiornaHeaderStatus("loading", null);

  try {
    const giorni = parseInt(document.getElementById("filtroGiorni").value);
    const resp = await fetch("/api/aggiorna", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ giorni }),
    });
    const data = await resp.json();

    if (data.success) {
      showToast("✅ Aggiornamento avviato! I dati si aggiorneranno tra pochi secondi.", "success");
      // Ricarica i dati dopo 3 secondi
      setTimeout(() => caricaDati(), 3000);
    } else {
      showToast(data.message || "❌ Errore durante l'aggiornamento", "error");
    }
  } catch (err) {
    showToast("❌ Impossibile contattare il server", "error");
  } finally {
    setTimeout(() => {
      btn.disabled = false;
      icona.classList.remove("spin");
    }, 3500);
  }
}

// ── Export CSV ─────────────────────────────────────────────────────────────

function esportaCSV() {
  showToast("📥 Download CSV in corso...", "info");
  window.location.href = "/api/export/csv";
}

// ── Polling stato aggiornamento ────────────────────────────────────────────

async function controllaStato() {
  try {
    const resp = await fetch("/api/stato");
    const data = await resp.json();
    if (data.stato_aggiornamento?.in_corso) {
      aggiornaHeaderStatus("loading", null);
    }
  } catch { /* silenzioso */ }
}

// ── Init ───────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  // Carica dati al boot
  caricaDati();

  // Polling ogni 60 secondi per controllare aggiornamenti
  setInterval(controllaStato, 60_000);

  // Auto-refresh ogni 5 minuti
  setInterval(() => caricaDati(), 5 * 60_000);

  // Keyboard shortcut: Ctrl+R per aggiorna
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "r" && !e.shiftKey) {
      e.preventDefault();
      aggiornaManuale();
    }
  });
});
