from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

CSV_PATH = Path("data/raw/submissions.csv")
OUT_DIR = Path("data")

COL = {
    "consent": "consent",
    "ministere": "ministere",
    "sexe": "sexe",
    "fonction": "fonction",
    "formation_genre": "formation_genre",
    "compr_genre": "compr_genre",
    "diff_sexe_genre": "diff_sexe_genre",
    "genre_biologique": "genre_biologique",
    "politiques_connaissance": "politiques_genre_connaissance",
    "importance_pol_pub": "importance_genre_politiques_publiques",
    "cellule_genre": "cellule_genre",
    "plan_action_genre": "plan_action_genre",
    "indicateurs_genre": "indicateurs_genre",
    "outils_guide_genre": "outils_guide_genre",
    "budget_genre_annuel": "budget_genre_annuel",
    "frequence_formations": "frequence_formations_genre",
    "importance_secteur": "importance_genre_secteur",
    "obstacles": "obstacles",
    "actions": "actions",
    "gtg_connaissance": "gtg_connaissance",
    "_submission_time": "_submission_time",
}

def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def read_csv_robust(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size < 5:
        return pd.DataFrame()

    head = path.read_bytes()[:200].lower()
    if b"<html" in head or b"<!doctype" in head:
        return pd.DataFrame()

    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=enc, engine="python")
            if df is not None and len(df.columns) > 0:
                return df
        except Exception:
            continue

    return pd.read_csv(path, encoding="latin-1", engine="python", on_bad_lines="skip")

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]

    # keep only consent == oui (if present)
    if COL["consent"] in df.columns:
        consent = df[COL["consent"]].astype(str).str.strip().str.lower()
        df = df[consent.eq("oui")].copy()

    return df

def pct(part: float, total: float) -> float:
    return round((part / total) * 100, 1) if total and total > 0 else 0.0

def safe_series(df: pd.DataFrame, col: str) -> pd.Series:
    if df is None or df.empty or col not in df.columns:
        return pd.Series([], dtype="object")
    s = df[col]
    if s.dtype != "object":
        s = s.astype(str)
    s = s.replace("nan", "").replace("None", "").astype(str).str.strip()
    s = s[s != ""]
    return s

def safe_value_counts(df: pd.DataFrame, col: str, top: int = 50) -> List[Dict[str, Any]]:
    s = safe_series(df, col)
    if s.empty:
        return []
    vc = s.value_counts().head(top)
    return [{"label": str(k), "value": int(v)} for k, v in vc.items()]

def safe_multi_counts(df: pd.DataFrame, col: str, top: int = 50) -> List[Dict[str, Any]]:
    s = safe_series(df, col)
    if s.empty:
        return []

    tokens: List[str] = []
    for raw in s.tolist():
        parts = [p.strip() for p in str(raw).split() if p.strip()]
        tokens.extend(parts)

    if not tokens:
        return []

    vc = pd.Series(tokens, dtype="object").value_counts().head(top)
    return [{"label": str(k), "value": int(v)} for k, v in vc.items()]

def build_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {"total_responses": 0}

    total = int(len(df))

    sexe = safe_series(df, COL["sexe"]).str.lower()
    female = int((sexe == "feminin").sum())
    male = int((sexe == "masculin").sum())

    ministries_covered = int(df[COL["ministere"]].nunique()) if COL["ministere"] in df.columns else 0

    fg = safe_series(df, COL["formation_genre"]).str.lower()
    fg_yes = int((fg == "oui").sum())
    fg_no = int((fg == "non").sum())

    cg = safe_series(df, COL["compr_genre"]).str.lower()
    cg_good = int((cg == "bonne").sum())
    cg_avg = int((cg == "moyenne").sum())
    cg_low = int((cg == "faible").sum())

    dsg = safe_series(df, COL["diff_sexe_genre"]).str.lower()
    dsg_yes = int((dsg == "oui").sum())
    dsg_no = int((dsg == "non").sum())

    gb = safe_series(df, COL["genre_biologique"]).str.lower()
    gb_correct = int((gb == "faux").sum())   # correct is "faux"
    gb_incorrect = int((gb == "vrai").sum())

    pg = safe_series(df, COL["politiques_connaissance"]).str.lower()
    pg_yes = int((pg == "oui").sum())
    pg_no = int((pg == "non").sum())

    ipp = safe_series(df, COL["importance_pol_pub"]).str.lower()
    ipp_yes = int((ipp == "oui").sum())
    ipp_no = int((ipp == "non").sum())

    unit = safe_series(df, COL["cellule_genre"]).str.lower()
    unit_yes = int((unit == "oui").sum())
    unit_no = int((unit == "non").sum())

    pag = safe_series(df, COL["plan_action_genre"]).str.lower()
    pag_yes = int((pag == "oui").sum())
    pag_no = int((pag == "non").sum())
    pag_np = int((pag == "np").sum())

    ig = safe_series(df, COL["indicateurs_genre"]).str.lower()
    ig_yes = int((ig == "oui").sum())
    ig_no = int((ig == "non").sum())
    ig_np = int((ig == "np").sum())

    og = safe_series(df, COL["outils_guide_genre"]).str.lower()
    og_yes = int((og == "oui").sum())
    og_no = int((og == "non").sum())

    budget_avg = 0.0
    with_budget = 0
    without_budget = total
    if COL["budget_genre_annuel"] in df.columns:
        b = pd.to_numeric(df[COL["budget_genre_annuel"]], errors="coerce")
        with_budget = int(b.notna().sum())
        without_budget = int(total - with_budget)
        budget_avg = round(float(b.dropna().mean()), 1) if with_budget > 0 else 0.0

    gtg = safe_series(df, COL["gtg_connaissance"]).str.lower()
    gtg_yes = int((gtg == "oui").sum())
    gtg_no = int((gtg == "non").sum())

    return {
        "total_responses": total,
        "female_respondents": female,
        "male_respondents": male,
        "pct_female": pct(female, total),
        "pct_male": pct(male, total),
        "ministries_covered": ministries_covered,
        "trained_on_gender": {"yes": fg_yes, "no": fg_no, "pct_yes": pct(fg_yes, total)},
        "gender_knowledge": {"good": cg_good, "average": cg_avg, "low": cg_low},
        "knows_sex_gender_difference": {"yes": dsg_yes, "no": dsg_no, "pct_yes": pct(dsg_yes, total)},
        "genre_not_biological_correct": {"correct": gb_correct, "incorrect": gb_incorrect, "pct_correct": pct(gb_correct, total)},
        "knows_gender_policies": {"yes": pg_yes, "no": pg_no, "pct_yes": pct(pg_yes, total)},
        "gender_important_public_policies": {"yes": ipp_yes, "no": ipp_no, "pct_yes": pct(ipp_yes, total)},
        "has_gender_unit": {"yes": unit_yes, "no": unit_no, "pct_yes": pct(unit_yes, total)},
        "has_gender_action_plan": {"yes": pag_yes, "no": pag_no, "partial": pag_np},
        "has_gender_indicators": {"yes": ig_yes, "no": ig_no, "partial": ig_np},
        "has_gender_guides": {"yes": og_yes, "no": og_no, "pct_yes": pct(og_yes, total)},
        "gender_budget": {"with_budget": with_budget, "without_budget": without_budget, "avg_budget_pct": budget_avg},
        "knows_GTG": {"yes": gtg_yes, "no": gtg_no, "pct_yes": pct(gtg_yes, total)},
    }

def build_breakdowns(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {
            "by_ministere": [],
            "by_sexe": [],
            "by_fonction": [],
            "by_compr_genre": [],
            "by_formation_genre": [],
            "by_diff_sexe_genre": [],
            "by_cellule_genre": [],
            "by_plan_action_genre": [],
            "by_indicateurs_genre": [],
            "by_outils_guide_genre": [],
            "by_frequence_formations": [],
            "by_importance_secteur": [],
            "obstacles": [],
            "actions": [],
        }

    return {
        "by_ministere": safe_value_counts(df, COL["ministere"], 80),
        "by_sexe": safe_value_counts(df, COL["sexe"], 10),
        "by_fonction": safe_value_counts(df, COL["fonction"], 30),
        "by_compr_genre": safe_value_counts(df, COL["compr_genre"], 10),
        "by_formation_genre": safe_value_counts(df, COL["formation_genre"], 10),
        "by_diff_sexe_genre": safe_value_counts(df, COL["diff_sexe_genre"], 10),
        "by_cellule_genre": safe_value_counts(df, COL["cellule_genre"], 10),
        "by_plan_action_genre": safe_value_counts(df, COL["plan_action_genre"], 10),
        "by_indicateurs_genre": safe_value_counts(df, COL["indicateurs_genre"], 10),
        "by_outils_guide_genre": safe_value_counts(df, COL["outils_guide_genre"], 10),
        "by_frequence_formations": safe_value_counts(df, COL["frequence_formations"], 10),
        "by_importance_secteur": safe_value_counts(df, COL["importance_secteur"], 10),
        "obstacles": safe_multi_counts(df, COL["obstacles"], 50),
        "actions": safe_multi_counts(df, COL["actions"], 50),
    }

def build_timeseries(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []

    col = COL["_submission_time"]
    if col not in df.columns:
        return []

    s = df[col].astype(str).str.strip()
    s = s.replace("nan", "").replace("None", "")
    s = s[s != ""]
    if s.empty:
        return []

    ts = pd.to_datetime(s, errors="coerce", dayfirst=True, utc=True)
    if ts.notna().sum() == 0:
        ts = pd.to_datetime(s, errors="coerce")

    tmp = pd.DataFrame({"_ts": ts}).dropna()
    if tmp.empty:
        return []

    tmp["_date"] = tmp["_ts"].dt.date.astype(str)
    g = tmp.groupby("_date").size().reset_index(name="count").sort_values("_date")
    return [{"date": str(r["_date"]), "count": int(r["count"])} for _, r in g.iterrows()]

def main() -> None:
    ensure_out_dir()

    df = read_csv_robust(CSV_PATH)
    df = clean_df(df)

    indicators = build_indicators(df)
    breakdowns = build_breakdowns(df)
    timeseries = build_timeseries(df)

    write_json(OUT_DIR / "indicators.json", indicators)
    write_json(OUT_DIR / "breakdowns.json", breakdowns)
    write_json(OUT_DIR / "timeseries.json", timeseries)

    print("OK build_json:", {
        "csv_bytes": CSV_PATH.stat().st_size if CSV_PATH.exists() else 0,
        "rows_after_consent_filter": int(len(df)) if df is not None else 0,
        "timeseries_points": len(timeseries),
    })

if __name__ == "__main__":
    main()
