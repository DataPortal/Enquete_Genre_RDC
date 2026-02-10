document.addEventListener("DOMContentLoaded", async ()=>{
  setActiveNav();
  const reco=await loadJSON("data/recommandations.json");
  const wrap=document.getElementById("recoWrap");
  wrap.innerHTML="";
  (reco.sections||[]).forEach(sec=>{
    const div=document.createElement("div");
    div.className="card";
    div.style.gridColumn="span 6";
    div.innerHTML=`<h2>${sec.titre}</h2><p class="sub">${sec.description||""}</p>`;
    const ul=document.createElement("ul");
    (sec.items||[]).forEach(it=>{ const li=document.createElement("li"); li.textContent=it; ul.appendChild(li); });
    div.appendChild(ul); wrap.appendChild(div);
  });
});
