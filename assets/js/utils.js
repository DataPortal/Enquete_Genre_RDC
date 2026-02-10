async function loadJSON(path){
  const res = await fetch(path, {cache:"no-store"});
  if(!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return await res.json();
}
function fmtPct(x){ if(x===null||x===undefined||Number.isNaN(Number(x))) return "—"; return `${Math.round(Number(x))}%`; }
function fmtNum(x){ if(x===null||x===undefined||Number.isNaN(Number(x))) return "—"; return Number(x).toLocaleString(undefined,{maximumFractionDigits:0}); }
function setActiveNav(){
  const path=(location.pathname.split("/").pop()||"index.html").toLowerCase();
  const map={"index.html":"home","analyse.html":"analyse","ministeres.html":"ministeres","recommandations.html":"reco"};
  const key=map[path]||"home";
  document.querySelectorAll(".nav-link").forEach(a=>{ if(a.dataset.nav===key) a.classList.add("active"); });
}
function setText(id, value){ const el=document.getElementById(id); if(el) el.textContent=value; }
function downloadText(filename, text){
  const blob=new Blob([text],{type:"text/plain;charset=utf-8"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a"); a.href=url; a.download=filename;
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}
function toCSV(rows){
  if(!rows.length) return "";
  const headers=Object.keys(rows[0]);
  const esc=(v)=>`"${String(v??"").replaceAll('"','""')}"`;
  return [headers.join(","), ...rows.map(r=>headers.map(h=>esc(r[h])).join(","))].join("\n");
}
