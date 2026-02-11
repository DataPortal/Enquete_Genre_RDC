export async function loadJSON(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return await res.json();
}

export async function loadAll() {
  const [indicators, breakdowns, timeseries, crosstabs, quality] = await Promise.all([
    loadJSON("data/indicators.json"),
    loadJSON("data/breakdowns.json"),
    loadJSON("data/timeseries.json"),
    loadJSON("data/crosstabs.json"),
    loadJSON("data/quality.json"),
  ]);
  return { indicators, breakdowns, timeseries, crosstabs, quality };
}

export function fmtNumber(n) {
  if (n === null || n === undefined) return "";
  const x = typeof n === "number" ? n : Number(n);
  if (Number.isNaN(x)) return String(n);
  return x.toLocaleString("fr-FR");
}
