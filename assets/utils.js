async function loadJSON(path){
  const res = await fetch(path, {cache: "no-store"});
  if(!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return await res.json();
}
function fmtPct(x){
  if (x === null || x === undefined || Number.isNaN(Number(x))) return "—";
  return `${Math.round(Number(x))}%`;
}
function fmtNum(x){
  if (x === null || x === undefined || Number.isNaN(Number(x))) return "—";
  const n = Number(x);
  return n.toLocaleString(undefined, {maximumFractionDigits: 0});
}
function setActiveNav(){
  const path = (location.pathname.split("/").pop() || "index.html").toLowerCase();
  const map = { "index.html":"home", "analyse.html":"analyse", "ministeres.html":"ministeres", "recommandations.html":"reco" };
  const key = map[path] || "home";
  document.querySelectorAll(".nav-link").forEach(a=>{
    if(a.dataset.nav === key) a.classList.add("active");
  });
}
function setText(id, value){
  const el = document.getElementById(id);
  if(el) el.textContent = value;
}
