import { loadAll, fmtNumber } from "./data.js";

function $(id) { return document.getElementById(id); }

function renderKPIs(indicators) {
  const box = $("kpis");
  if (!box) return;

  if (!Array.isArray(indicators) || indicators.length === 0) {
    box.innerHTML = `<div class="callout">Aucune donnée disponible (indicators.json est vide).</div>`;
    return;
  }

  box.innerHTML = indicators.map(k => `
    <div class="card">
      <div class="sub">${k.label}</div>
      <div class="kpi">
        <div class="value">${typeof k.value === "number" ? fmtNumber(k.value) : (k.value || "")}</div>
        <div class="trend">${k.unit || ""}</div>
      </div>
    </div>
  `).join("");
}

function renderBreakdownList(title, arr, mountId) {
  const box = $(mountId);
  if (!box) return;
  if (!Array.isArray(arr) || arr.length === 0) {
    box.innerHTML = `<div class="callout">Aucune donnée pour: ${title}</div>`;
    return;
  }
  box.innerHTML = `
    <div class="card">
      <h2>${title}</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Valeur</th><th>Nombre</th></tr></thead>
          <tbody>
            ${arr.map(x => `<tr><td>${x.key}</td><td>${fmtNumber(x.value)}</td></tr>`).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

async function main() {
  try {
    const { indicators, breakdowns } = await loadAll();
    renderKPIs(indicators);

    // exemples de rendus
    renderBreakdownList("Réponses par ministère", breakdowns?.ministere, "b_ministere");
    renderBreakdownList("Réponses par sexe", breakdowns?.sexe, "b_sexe");
    renderBreakdownList("Compréhension du genre", breakdowns?.compr_genre, "b_compr");
    renderBreakdownList("Obstacles (codes)", breakdowns?.obstacles_codes, "b_obstacles");
    renderBreakdownList("Actions (codes)", breakdowns?.actions_codes, "b_actions");
  } catch (e) {
    const root = $("root");
    if (root) root.innerHTML = `<div class="callout">Erreur chargement données: ${e.message}</div>`;
    console.error(e);
  }
}

main();
