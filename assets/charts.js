function clearCanvas(ctx){ ctx.clearRect(0,0,ctx.canvas.width, ctx.canvas.height); }
function setupHiDPI(canvas){
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.round(rect.width * dpr);
  canvas.height = Math.round(rect.height * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr,0,0,dpr,0,0);
  return ctx;
}
function drawBarChart(canvas, labels, values){
  const ctx = setupHiDPI(canvas);
  const w = canvas.getBoundingClientRect().width;
  const h = canvas.getBoundingClientRect().height;
  clearCanvas(ctx);

  const padding = 28;
  const chartW = w - padding*2;
  const chartH = h - padding*2 - 20;
  const maxV = Math.max(...values, 1);

  ctx.strokeStyle = "rgba(17,24,39,.15)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padding, padding);
  ctx.lineTo(padding, padding + chartH);
  ctx.lineTo(padding + chartW, padding + chartH);
  ctx.stroke();

  const barGap = 10;
  const barW = Math.max(10, (chartW - barGap*(values.length-1)) / values.length);

  values.forEach((v, i)=>{
    const x = padding + i*(barW+barGap);
    const barH = (v/maxV)*chartH;
    const y = padding + chartH - barH;

    ctx.fillStyle = "rgba(68,139,202,.55)";
    ctx.fillRect(x, y, barW, barH);
    ctx.fillStyle = "rgba(245,130,32,.65)";
    ctx.fillRect(x, y, barW, 3);

    ctx.fillStyle = "rgba(17,24,39,.8)";
    ctx.font = "12px system-ui, Segoe UI, Arial";
    ctx.textAlign = "center";
    ctx.fillText(String(Math.round(v)), x + barW/2, y - 6);

    const lab = labels[i] || "";
    const short = lab.length > 12 ? lab.slice(0,11)+"…" : lab;
    ctx.fillStyle = "rgba(107,114,128,1)";
    ctx.fillText(short, x + barW/2, padding + chartH + 16);
  });
}
function drawDoughnut(canvas, segments, opts={}){
  const ctx = setupHiDPI(canvas);
  const w = canvas.getBoundingClientRect().width;
  const h = canvas.getBoundingClientRect().height;
  clearCanvas(ctx);

  const total = segments.reduce((a,s)=>a + (Number(s.value)||0), 0) || 1;
  const cx = w/2, cy = h/2;
  const rOuter = Math.min(w,h)*0.33;
  const rInner = rOuter*0.62;

  let start = -Math.PI/2;
  segments.forEach((s, idx)=>{
    const v = (Number(s.value)||0);
    const ang = (v/total) * Math.PI*2;
    const end = start + ang;
    const base = idx % 2 === 0 ? [68,139,202] : [245,130,32];
    const alpha = 0.30 + (idx%6)*0.10;
    ctx.fillStyle = `rgba(${base[0]},${base[1]},${base[2]},${Math.min(alpha,0.9)})`;

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, rOuter, start, end);
    ctx.closePath();
    ctx.fill();

    start = end;
  });

  ctx.globalCompositeOperation = "destination-out";
  ctx.beginPath();
  ctx.arc(cx, cy, rInner, 0, Math.PI*2);
  ctx.closePath();
  ctx.fill();
  ctx.globalCompositeOperation = "source-over";

  ctx.fillStyle = "rgba(17,24,39,.85)";
  ctx.font = "700 18px system-ui, Segoe UI, Arial";
  ctx.textAlign = "center";
  ctx.fillText(opts.centerText || "", cx, cy+6);

  ctx.font = "12px system-ui, Segoe UI, Arial";
  ctx.textAlign = "left";
  let lx = 16, ly = 16;
  segments.slice(0,6).forEach((s, idx)=>{
    const base = idx % 2 === 0 ? [68,139,202] : [245,130,32];
    ctx.fillStyle = `rgba(${base[0]},${base[1]},${base[2]},0.75)`;
    ctx.fillRect(lx, ly + idx*16, 10, 10);
    ctx.fillStyle = "rgba(107,114,128,1)";
    const pct = total ? Math.round((Number(s.value)||0)/total*100) : 0;
    ctx.fillText(`${s.label}: ${pct}%`, lx+14, ly + idx*16 + 9);
  });
}
