let _ministeres=[], _filtered=[], _currentSort={key:"score",dir:"desc"};

function renderTable(rows){
  const tbody=document.getElementById("tblBody");
  tbody.innerHTML="";
  rows.forEach(r=>{
    const tr=document.createElement("tr");
    tr.innerHTML=`
      <td>${r.ministere}</td>
      <td>${fmtPct(r.formes_genre)}</td>
      <td>${r.point_focal ? '<span class="pill"><span class="mini"></span>Oui</span>' :
        '<span class="pill"><span class="mini" style="background: var(--uw-orange)"></span>Non</span>'}</td>
      <td>${fmtPct(r.integration)}</td>
      <td><strong>${fmtNum(r.score)}</strong></td>`;
    tbody.appendChild(tr);
  });
}

function sortRows(rows,key,dir){
  const sign=dir==="asc"?1:-1;
  return [...rows].sort((a,b)=>{
    const av=a[key], bv=b[key];
    if(key==="ministere") return sign*String(av||"").localeCompare(String(bv||""),"fr");
    if(key==="point_focal") return sign*((av===bv)?0:(av?1:-1));
    return sign*((Number(av)||0)-(Number(bv)||0));
  });
}

function setHeaderSortUI(key,dir){
  document.querySelectorAll("th[data-sort]").forEach(th=>{
    th.classList.remove("sort-asc","sort-desc");
    if(th.dataset.sort===key) th.classList.add(dir==="asc"?"sort-asc":"sort-desc");
  });
}

function applyFilters(){
  const q=(document.getElementById("qMinistere").value||"").toLowerCase().trim();
  const pf=document.getElementById("fPointFocal").value;

  _filtered=_ministeres.filter(r=>{
    const okName=!q || String(r.ministere||"").toLowerCase().includes(q);
    const okPf=(pf==="all")||(pf==="yes"&&r.point_focal)||(pf==="no"&&!r.point_focal);
    return okName&&okPf;
  });

  _filtered=sortRows(_filtered,_currentSort.key,_currentSort.dir);
  renderTable(_filtered);

  const top=sortRows(_filtered,"score","desc").slice(0,10);
  drawBarChart(document.getElementById("chartMinisteres"), top.map(x=>x.ministere), top.map(x=>x.score));
  setText("countMinisteres", fmtNum(_filtered.length));
}

document.addEventListener("DOMContentLoaded", async ()=>{
  setActiveNav();
  _ministeres=await loadJSON("data/ministeres.json");

  document.getElementById("qMinistere").addEventListener("input", applyFilters);
  document.getElementById("fPointFocal").addEventListener("change", applyFilters);
  document.getElementById("fTri").addEventListener("change",(e)=>{
    const v=e.target.value;
    if(v==="score_desc") _currentSort={key:"score",dir:"desc"};
    if(v==="score_asc") _currentSort={key:"score",dir:"asc"};
    if(v==="formes_desc") _currentSort={key:"formes_genre",dir:"desc"};
    if(v==="formes_asc") _currentSort={key:"formes_genre",dir:"asc"};
    if(v==="alpha_asc") _currentSort={key:"ministere",dir:"asc"};
    if(v==="alpha_desc") _currentSort={key:"ministere",dir:"desc"};
    setHeaderSortUI(_currentSort.key,_currentSort.dir);
    applyFilters();
  });

  document.querySelectorAll("th[data-sort]").forEach(th=>{
    th.addEventListener("click",()=>{
      const key=th.dataset.sort;
      const dir=(_currentSort.key===key && _currentSort.dir==="asc")?"desc":"asc";
      _currentSort={key,dir};
      setHeaderSortUI(key,dir);
      applyFilters();
    });
  });

  document.getElementById("btnExport").addEventListener("click",()=>{
    const rows=_filtered.map(r=>({
      ministere:r.ministere,
      formes_genre_pct:r.formes_genre,
      point_focal:r.point_focal?"Oui":"Non",
      integration_pct:r.integration,
      score:r.score
    }));
    downloadText("ministeres_table.csv", toCSV(rows));
  });

  setHeaderSortUI(_currentSort.key,_currentSort.dir);
  applyFilters();
});
