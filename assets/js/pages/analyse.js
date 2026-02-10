document.addEventListener("DOMContentLoaded", async ()=>{
  setActiveNav();
  const [summary, indicateurs, meta] = await Promise.all([
    loadJSON("data/summary.json"),
    loadJSON("data/indicateurs.json"),
    loadJSON("data/meta.json").catch(()=>({}))
  ]);
  setText("kpiScore", fmtNum(summary.score_moyen_connaissance));
  drawDoughnut(document.getElementById("chartFonction"), (indicateurs.fonction||[]).slice(0,7), {centerText:"Fonction"});
  const labels=meta.obstacle_labels||{};
  const obs=(indicateurs.obstacles||[]).map(o=>({label: labels[o.label]||o.label, value:o.value}));
  drawBarChart(document.getElementById("chartObstacles"), obs.slice(0,10).map(o=>o.label), obs.slice(0,10).map(o=>o.value));
});
