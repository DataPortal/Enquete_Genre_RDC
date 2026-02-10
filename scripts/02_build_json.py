import json
from pathlib import Path
import pandas as pd
from pandas.errors import EmptyDataError

CSV_PATH = Path("data/raw/submissions.csv")
OUT_DIR = Path("data")

# Champs attendus (d'après tes en-têtes)
COLS = {
    "submission_time": "_submission_time",
    "sexe": "sexe",
    "ministere": "ministere",
    "fonction": "fonction",
    "formation_genre": "formation_genre",
    "compr_genre": "compr_genre",
    "diff_sexe_genre": "diff_sexe_genre",
    "genre_biologique": "genre_biologique",
    "pol_connaissance": "politiques_genre_connaissance",
    "cellule_genre": "cellule_genre",
    "nb_pf": "nb_points_focaux",
    "plan_action": "plan_action_genre",
    "indicateurs": "indicateurs_genre",
    "outils": "outils_guide_genre",
    "budget": "budget_genre_annuel",
    "freq_form": "frequence_formations_genre",
    "importance_secteur": "importance_genre_secteur",
    "gtg": "gtg_connaissance",
}

def decode_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8", engine="python", on_bad_lines="skip")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", engine="python", on_bad_lines="skip")
    except EmptyDataError:
        return pd.DataFrame()

def norm_yes(x):
    if pd.isna(x): 
        return None
    s = str(x).strip().lower()
    if s in ("oui", "yes", "y", "1", "true"): 
        return True
    if s in ("non", "no", "n", "0", "false"): 
        return False
    if s in ("np", "n/p", "partiellement", "je ne sais pas"): 
        return None
    return None

def safe_value_counts(series: pd.Series, top=50):
    if series is None or series.empty:
        return []
    vc = (
        series.astype(str)
        .replace("nan", pd.NA)
        .dropna()
        .value_counts()
        .head(top)
    )
    return [{"key": k, "value": int(v)} for k, v in vc.items()]

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = decode_csv(CSV_PATH)

    # Si vide => JSON vides mais valides
    if df.empty or len(df.columns) == 0:
        meta = {"generated": "empty", "rows": 0}
        write_json(OUT_DIR / "meta.json", meta)
        write_json(OUT_DIR / "indicators.json", [])
        write_json(OUT_DIR / "breakdowns.json", [])
        write_json(OUT_DIR / "timeseries.json", [])
        print("INFO: No data. Wrote empty JSON outputs.")
        return

    # Parse time
    if COLS["submission_time"] in df.columns:
        df["_ts"] = pd.to_datetime(df[COLS["submission_time"]], errors="coerce", utc=True)
    else:
        df["_ts"] = pd.NaT

    rows = int(len(df))
    last_ts = df["_ts"].dropna().max()
    meta = {
        "generated": "ok",
        "rows": rows,
        "last_submission_time": (last_ts.isoformat() if pd.notna(last_ts) else None),
    }

    # Indicators
    indicators = []

    def add_rate(name, series_bool):
        series_bool = series_bool.dropna()
        if len(series_bool) == 0:
            indicators.append({"id": name, "label": name, "value": None, "n": 0})
            return
        val = float(series_bool.mean())
        indicators.append({"id": name, "label": name, "value": round(val, 3), "n": int(len(series_bool))})

    # Build boolean series from columns
    def get_bool(col):
        if col not in df.columns:
            return pd.Series([], dtype="float")
        return df[col].apply(norm_yes)

    add_rate("formation_genre_oui_rate", get_bool(COLS["formation_genre"]))
    add_rate("diff_sexe_genre_oui_rate", get_bool(COLS["diff_sexe_genre"]))
    add_rate("politiques_genre_connaissance_oui_rate", get_bool(COLS["pol_connaissance"]))
    add_rate("cellule_genre_oui_rate", get_bool(COLS["cellule_genre"]))
    add_rate("plan_action_genre_oui_rate", get_bool(COLS["plan_action"]))
    add_rate("indicateurs_genre_oui_rate", get_bool(COLS["indicateurs"]))
    add_rate("outils_guide_genre_oui_rate", get_bool(COLS["outils"]))
    add_rate("gtg_connaissance_oui_rate", get_bool(COLS["gtg"]))

    # Budget moyenne (si présent)
    if COLS["budget"] in df.columns:
        b = pd.to_numeric(df[COLS["budget"]], errors="coerce")
        if b.notna().any():
            indicators.append({
                "id": "budget_genre_annuel_mean",
                "label": "budget_genre_annuel_mean",
                "value": round(float(b.mean()), 2),
                "n": int(b.notna().sum()),
            })
        else:
            indicators.append({"id": "budget_genre_annuel_mean", "label": "budget_genre_annuel_mean", "value": None, "n": 0})

    # Breakdown distributions
    breakdowns = []

    def add_breakdown(key, col):
        if col in df.columns:
            breakdowns.append({"id": key, "label": key, "items": safe_value_counts(df[col])})
        else:
            breakdowns.append({"id": key, "label": key, "items": []})

    add_breakdown("sexe", COLS["sexe"])
    add_breakdown("ministere", COLS["ministere"])
    add_breakdown("fonction", COLS["fonction"])
    add_breakdown("compr_genre", COLS["compr_genre"])
    add_breakdown("frequence_formations_genre", COLS["freq_form"])
    add_breakdown("importance_genre_secteur", COLS["importance_secteur"])

    # Timeseries (soumissions par jour)
    ts = []
    if df["_ts"].notna().any():
        per_day = df.dropna(subset=["_ts"]).set_index("_ts").resample("D").size()
        ts = [{"date": d.date().isoformat(), "count": int(c)} for d, c in per_day.items()]

    # Write outputs
    write_json(OUT_DIR / "meta.json", meta)
    write_json(OUT_DIR / "indicators.json", indicators)
    write_json(OUT_DIR / "breakdowns.json", breakdowns)
    write_json(OUT_DIR / "timeseries.json", ts)

    print(f"OK: wrote JSON outputs. rows={rows}")

if __name__ == "__main__":
    main()
