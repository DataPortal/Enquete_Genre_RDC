import json
from pathlib import Path
from datetime import datetime
import pandas as pd


OUT_DIR = Path("data")
RAW_CSV = Path("data/raw/submissions.csv")


def read_csv_safely(path: Path) -> pd.DataFrame:
    raw = path.read_bytes()
    if len(raw) < 10:
        raise ValueError(f"CSV too small/empty: {path} ({len(raw)} bytes)")
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, engine="python", on_bad_lines="skip")
        except Exception:
            pass
    return pd.read_csv(path, engine="python", on_bad_lines="skip")


def normalize_text(s):
    if pd.isna(s):
        return ""
    return str(s).strip()


def parse_multiselect(cell: str):
    """
    Kobo select_multiple often exports as: 'obs1 obs3 obs5'
    """
    cell = normalize_text(cell)
    if not cell:
        return []
    return [x.strip() for x in cell.split() if x.strip()]


def safe_dt(s: str):
    s = normalize_text(s)
    if not s:
        return None
    # Kobo examples: "10/02/2026 09:18" or ISO
    for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        return pd.to_datetime(s, utc=False, errors="coerce").to_pydatetime()
    except Exception:
        return None


def count_values(df: pd.DataFrame, col: str):
    if col not in df.columns:
        return []
    s = df[col].astype(str).fillna("").replace("nan", "")
    vc = s.value_counts(dropna=False)
    out = []
    for k, v in vc.items():
        kk = str(k).strip()
        if kk == "" or kk.lower() == "nan":
            kk = "(vide)"
        out.append({"key": kk, "value": int(v)})
    return out


def build_binary_from_multiselect(df: pd.DataFrame, col: str, prefix: str, universe: list[str]):
    """
    Create counts for each code in universe using either:
    - explicit binary columns like obstacles/obs1 (0/1), or
    - parsing select_multiple string in df[col]
    """
    counts = []
    # if binary columns exist, use them
    binary_cols = [f"{prefix}/{code}" for code in universe]
    if all(c in df.columns for c in binary_cols):
        for code in universe:
            c = f"{prefix}/{code}"
            # accept 1, "1", True
            val = pd.to_numeric(df[c], errors="coerce").fillna(0)
            counts.append({"key": code, "value": int((val > 0).sum())})
        return counts

    # else parse multiselect
    if col not in df.columns:
        return []
    parsed = df[col].apply(parse_multiselect)
    for code in universe:
        counts.append({"key": code, "value": int(parsed.apply(lambda xs: code in xs).sum())})
    return counts


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df_all = read_csv_safely(RAW_CSV)

    # Keep only consented submissions if consent exists
    df = df_all.copy()
    if "consent" in df.columns:
        df = df[df["consent"].astype(str).str.strip().eq("oui")].copy()

    # If still empty, produce empty but informative quality.json
    if df.shape[0] == 0:
        write_json(OUT_DIR / "indicators.json", [])
        write_json(OUT_DIR / "breakdowns.json", [])
        write_json(OUT_DIR / "timeseries.json", [])
        write_json(
            OUT_DIR / "quality.json",
            {
                "rows_total": int(df_all.shape[0]),
                "rows_consented": 0,
                "note": "No consented submissions yet (consent!='oui' or missing).",
            },
        )
        return

    # ---------- Indicators (KPIs) ----------
    n = int(df.shape[0])

    last_dt = None
    if "_submission_time" in df.columns:
        dts = df["_submission_time"].apply(safe_dt).dropna()
        if len(dts) > 0:
            last_dt = max(dts)

    indicators = [
        {"key": "responses", "label": "Soumissions (consentement = oui)", "value": n, "unit": "réponses"},
        {
            "key": "last_submission",
            "label": "Dernière soumission",
            "value": last_dt.isoformat() if last_dt else "",
            "unit": "",
        },
    ]

    # Optional rates
    if "sexe" in df.columns:
        f = int((df["sexe"].astype(str).str.strip() == "feminin").sum())
        m = int((df["sexe"].astype(str).str.strip() == "masculin").sum())
        indicators.append({"key": "female_share", "label": "Part femmes", "value": round(100 * f / n, 1), "unit": "%"})
        indicators.append({"key": "male_share", "label": "Part hommes", "value": round(100 * m / n, 1), "unit": "%"})

    # ---------- Breakdowns ----------
    breakdowns = {
        "ministere": count_values(df, "ministere"),
        "sexe": count_values(df, "sexe"),
        "fonction": count_values(df, "fonction"),
        "annees_experience_ministere": count_values(df, "annees_experience_ministere"),
        "formation_genre": count_values(df, "formation_genre"),
        "compr_genre": count_values(df, "compr_genre"),
        "diff_sexe_genre": count_values(df, "diff_sexe_genre"),
        "genre_biologique": count_values(df, "genre_biologique"),
        "politiques_genre_connaissance": count_values(df, "politiques_genre_connaissance"),
        "cellule_genre": count_values(df, "cellule_genre"),
        "plan_action_genre": count_values(df, "plan_action_genre"),
        "indicateurs_genre": count_values(df, "indicateurs_genre"),
        "outils_guide_genre": count_values(df, "outils_guide_genre"),
        "frequence_formations_genre": count_values(df, "frequence_formations_genre"),
        "importance_genre_secteur": count_values(df, "importance_genre_secteur"),
        "gtg_connaissance": count_values(df, "gtg_connaissance"),
    }

    # Obstacles + Actions + Sous-groupes GTG (codes)
    obstacle_codes = ["obs1", "obs2", "obs3", "obs4", "obs5", "obs6", "obs7", "obs8"]
    action_codes = ["act1", "act2", "act3", "act4", "act5", "act6", "act7"]
    sgtgtg_codes = ["vbg", "essjf", "rpeaf", "pplf"]

    breakdowns["obstacles_codes"] = build_binary_from_multiselect(df, "obstacles", "obstacles", obstacle_codes)
    breakdowns["actions_codes"] = build_binary_from_multiselect(df, "actions", "actions", action_codes)
    breakdowns["sgtgtg_codes"] = build_binary_from_multiselect(df, "sgtgtg_connus", "sgtgtg_connus", sgtgtg_codes)

    # ---------- Timeseries (daily) ----------
    timeseries = []
    if "_submission_time" in df.columns:
        tmp = df.copy()
        tmp["_dt"] = tmp["_submission_time"].apply(safe_dt)
        tmp = tmp.dropna(subset=["_dt"])
        if len(tmp) > 0:
            tmp["_day"] = tmp["_dt"].apply(lambda d: d.date().isoformat())
            vc = tmp["_day"].value_counts().sort_index()
            timeseries = [{"day": k, "value": int(v)} for k, v in vc.items()]

    # ---------- Crosstabs (useful for analysis) ----------
    crosstabs = {}
    if "sexe" in df.columns and "compr_genre" in df.columns:
        ct = pd.crosstab(df["sexe"], df["compr_genre"])
        crosstabs["sexe_x_compr_genre"] = {
            "rows": [str(i) for i in ct.index.tolist()],
            "cols": [str(c) for c in ct.columns.tolist()],
            "values": ct.astype(int).values.tolist(),
        }

    if "ministere" in df.columns and "formation_genre" in df.columns:
        ct = pd.crosstab(df["ministere"], df["formation_genre"])
        crosstabs["ministere_x_formation_genre"] = {
            "rows": [str(i) for i in ct.index.tolist()],
            "cols": [str(c) for c in ct.columns.tolist()],
            "values": ct.astype(int).values.tolist(),
        }

    # ---------- Quality ----------
    quality = {
        "rows_total": int(df_all.shape[0]),
        "rows_consented": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_rate_top10": [],
    }
    miss = (df.isna().mean() * 100).sort_values(ascending=False)
    quality["missing_rate_top10"] = [{"col": k, "pct": round(float(v), 1)} for k, v in miss.head(10).items()]

    # Write files
    write_json(OUT_DIR / "indicators.json", indicators)
    write_json(OUT_DIR / "breakdowns.json", breakdowns)
    write_json(OUT_DIR / "timeseries.json", timeseries)
    write_json(OUT_DIR / "crosstabs.json", crosstabs)
    write_json(OUT_DIR / "quality.json", quality)

    print("Built JSON:",
          "indicators.json, breakdowns.json, timeseries.json, crosstabs.json, quality.json")


if __name__ == "__main__":
    main()
