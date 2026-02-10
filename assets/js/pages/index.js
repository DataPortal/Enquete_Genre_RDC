document.addEventListener("DOMContentLoaded", async ()=>{
  setActiveNav();
  const [summary, indicateurs, ministeres, meta] = await Promise.all([
    loadJSON("data/summary.json"),
    loadJSON("data/indicateurs.json"),
    loadJSON("data/ministeres.json"),
    loadJSON("data/meta.json").catch(()=>({}))
  ]);
  setText("kpiRespondants", fmtNum(summary.total_repondants));
  setText("kpiFormes", fmtPct(summary.pourcentage_formes_genre));
  setText("kpiPF", fmtPct(summary.ministeres_avec_point_focal));
  setText("kpiIntegr", fmtPct(summary.integration_politiques));
  setText("periodeCollecte", summary.periode_collecte || "—");
  setText("noteMethodo", summary.note_methodo || "—");

  drawBarChart(document.getElementById("chartScore"),
               (indicateurs.score_bins||[]).map(x=>x.label),
               (indicateurs.score_bins||[]).map(x=>x.value));
  drawDoughnut(document.getElementById("chartSexe"), indicateurs.sexe||[], {centerText:"Profil"});

  const sorted=[...(ministeres||[])].sort((a,b)=>(b.score||0)-(a.score||0));
  const top=sorted[0]||{}, low=sorted[sorted.length-1]||{};
  setText("insightTopMin", top.ministere||"—"); setText("insightTopScore", fmtNum(top.score));
  setText("insightLowMin", low.ministere||"—"); setText("insightLowScore", fmtNum(low.score));

  const labels=(meta.obstacle_labels||{});
  const obs=[...(indicateurs.obstacles||[])].sort((a,b)=>(b.value||0)-(a.value||0));
  const o1=obs[0]||{};
  setText("insightObs1", labels[o1.label] || o1.label || "—");
  setText("insightObsN", fmtNum(o1.value));

  if(meta.key_message){ const el=document.getElementById("keyMessage"); if(el) el.textContent=meta.key_message; }
});
