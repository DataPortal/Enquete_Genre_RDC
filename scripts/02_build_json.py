import json
from pathlib import Path
import pandas as pd

CSV_PATH = Path("data/raw/submissions.csv")
OUT_DIR = Path("data")

# Colonnes attendues (d’après tes en-têtes Kobo)
COLS = {
    "ministere": "ministere",
    "sexe": "sexe",
    "fonction": "fonction",
    "formation_genre": "formation_genre",
    "compr_genre": "compr_genre",
    "diff_sexe_genre": "diff_sexe_genre",
    "genre_biologique": "genre_biologique",
    "politiques_genre_connaissance": "politiques_genre_connaissance",
    "importance_genre_politiques_publiques": "importance_genre_politiques_publiques",
    "cellule_genre": "cellule_genre",
    "plan_action_genre": "plan_action_genre",
    "indicateurs_genre": "indicateurs_genre",
    "outils_guide_genre": "outils_guide_genre",
    "frequence_formations_genre": "frequence_formations_genre",
    "importance_genre_secteur": "importance_genre_secteur",
    "gtg_connaissance": "gtg_connaissance",
    "_submission_time": "_submission_time",
    "_id": "_id",
}

YES = {"oui", "yes", "1", True}
NO = {"non", "no", "0", False}
BOOL_TRUE = {"1", 1, True, "true", "True", "oui", "OUI", "yes", "YES"}

def read_csv_robust(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size < 10:
        return pd.DataFrame()

    # Kobo exports sometimes are UTF-8 but may contain weird chars
    # Try utf-8 then latin-1 fallback.
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=enc, engine="python")
            if len(df.columns) > 0:
                return df
        except Exception:
            continue

    # Last resort
    return pd.read_csv(path, encoding="latin-1", engine="python", on_bad_lines="skip")

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    # Normalize column names
    df.columns = [str(c).strip() for c in df.columns]

    # Strip whitespace for object fields
    for c in df.columns:
        if df[c].dtype == "object":
            df[c] = df[c].astype(str).str.strip()

    # Keep only consent == "oui" if available
    if "consent" in df.columns:
        df = df[df["consent"].astype(str).str.lower().eq("oui")]

    return df

def pct_yes(series: pd.Series) -> float:
    if series is None or series.empty:
        return 0.0
    s = series.astype(str).str.lower().str.strip()
    return round((s.eq("oui").sum() / max(len(s), 1)) * 100, 1)

def safe_value_counts(df: pd.DataFrame, col: str, top: int = 20):
    if col not in df.columns or df.empty:
        return []
    vc = df[col].astype(str).replace("nan", "").replace("None", "").str.strip()
    vc = vc[vc != ""].value_counts().head(top)
    return [{"label": k, "value": int(v)} for k, v in vc.items()]

def ensure_out_dir():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def build_indicators(df: pd.DataFrame) -> list:
    n = len(df)
    if n == 0:
        # Always return structured empty indicators (not [])
        return [
            {"key": "responses_total", "label": "Nombre de réponses", "value": 0},
            {"key": "female_share", "label": "Part des femmes (%)", "value": 0},
        ]

    indicators = []
    indicators.append({"key": "responses_total", "label": "Nombre de réponses", "value": int(n)})

    if "sexe" in df.columns:
        s = df["sexe"].astype(str).str.lower().str.strip()
        female = (s == "feminin").sum()
        indicators.append({"key": "female_share", "label": "Part des femmes (%)", "value": round(female / n * 100, 1)})
    else:
        indicators.append({"key": "female_share", "label": "Part des femmes (%)", "value": 0})

    # Core gender knowledge indicators
    indicators.append({"key": "trained_gender_pct", "label": "Formé au genre (%)", "value": pct_yes(df.get("formation_genre"))})
    indicators.append({"key": "knows_sex_gender_pct", "label": "Différence sexe/genre connue (%)", "value": pct_yes(df.get("diff_sexe_genre"))})

    # Statement “genre is biological” should be FALSE ideally; measure correct answers
    if "genre_biologique" in df.columns:
        s = df["genre_biologique"].astype(str).str.lower().str.strip()
        correct = (s == "faux").sum()
        indicators.append({"key": "genre_not_bio_correct_pct", "label": "Genre ≠ biologique (réponse correcte, %)", "value": round(correct / n * 100, 1)})
    else:
        indicators.append({"key": "genre_not_bio_correct_pct", "label": "Genre ≠ biologique (réponse correcte, %)", "value": 0})

    indicators.append({"key": "knows_policies_pct", "label": "Connaît une politique genre (%)", "value": pct_yes(df.get("politiques_genre_connaissance"))})
    indicators.append({"key": "public_policy_importance_pct", "label": "Genre important en politiques publiques (%)", "value": pct_yes(df.get("importance_genre_politiques_publiques"))})
    indicators.append({"key": "has_gender_cell_pct", "label": "Dispose d’une cellule genre (%)", "value": pct_yes(df.get("cellule_genre"))})
    indicators.append({"key": "has_gender_plan_pct", "label": "Plan/stratégie genre (%)", "value": pct_yes(df.get("plan_action_genre"))})
    indicators.append({"key": "gender_indicators_pct", "label": "Indicateurs sensibles au genre (%)", "value": pct_yes(df.get("indicateurs_genre"))})
    indicators.append({"key": "has_guides_pct", "label": "Accès à outils/guides (%)", "value": pct_yes(df.get("outils_guide_genre"))})
    indicators.append({"key": "gtg_known_pct", "label": "Connaît le GTG (%)", "value": pct_yes(df.get("gtg_connaissance"))})

    return indicators

def build_breakdowns(df: pd.DataFrame) -> dict:
    return {
        "by_ministere": safe_value_counts(df, "ministere", 50),
        "by_sexe": safe_value_counts(df, "sexe", 10),
        "by_fonction": safe_value_counts(df, "fonction", 20),
        "by_compr_genre": safe_value_counts(df, "compr_genre", 10),
        "by_freq_formations": safe_value_counts(df, "frequence_formations_genre", 10),
        "by_obstacles": safe_value_counts(df, "obstacles", 30),  # select_multiple usually space-separated
        "by_actions": safe_value_counts(df, "actions", 30),
    }

def build_timeseries(df: pd.DataFrame) -> list:
    if df.empty:
        return []

    if "_submission_time" not in df.columns:
        return []

    # Kobo times can be "10/02/2026 09:18" or ISO; parse flexibly
    ts = pd.to_datetime(df["_submission_time"], errors="coerce", dayfirst=True, utc=True)
    tmp = df.copy()
    tmp["_ts"] = ts
    tmp = tmp.dropna(subset=["_ts"])
    if tmp.empty:
        return []

    tmp["_date"] = tmp["_ts"].dt.date.astype(str)
    g = tmp.groupby("_date").size().reset_index(name="count").sort_values("_date")
    return [{"date": r["_date"], "count": int(r["count"])} for _, r in g.iterrows()]

def main():
    ensure_out_dir()

    df = read_csv_robust(CSV_PATH)
    df = clean_df(df)

    indicators = build_indicators(df)
    breakdowns = build_breakdowns(df)
    timeseries = build_timeseries(df)

    write_json(OUT_DIR / "indicators.json", indicators)
    write_json(OUT_DIR / "breakdowns.json", breakdowns)
    write_json(OUT_DIR / "timeseries.json", timeseries)

    print(f"OK: rows={len(df)} -> indicators={len(indicators)} breakdowns_keys={len(breakdowns.keys())} timeseries={len(timeseries)}")

if __name__ == "__main__":
    main()
