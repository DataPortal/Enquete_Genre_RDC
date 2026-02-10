import json
from pathlib import Path
import pandas as pd

YES = {"oui","yes","y","true","1","vrai"}
NO  = {"non","no","n","false","0","faux"}

# --- Helpers ---
def norm(x):
    if pd.isna(x): return ""
    return str(x).strip()

def is_yes(x): return norm(x).lower() in YES
def is_no(x):  return norm(x).lower() in NO

def pct(num, den):
    return int(round((num/den)*100)) if den else 0

def safe_int(x, default=0):
    try:
        return int(float(x))
    except Exception:
        return default

# --- Score connaissance (0–100) basé sur tes champs ---
def compute_score(row) -> int:
    points = 0
    total = 5

    # 1) Compréhension du genre (compr_genre : "bonne" / "faible" / ...)
    cg = norm(row.get("compr_genre")).lower()
    if cg in {"bonne", "bon", "good"}:
        points += 1
    elif cg in {"moyenne", "average"}:
        points += 0.5

    # 2) Distingue sexe vs genre (diff_sexe_genre : oui/non)
    if is_yes(row.get("diff_sexe_genre")):
        points += 1

    # 3) "Le genre est biologique" : bonne réponse attendue = FAUX
    gb = norm(row.get("genre_biologique")).lower()
    if gb in {"faux", "false"}:
        points += 1

    # 4) Connaissance des politiques genre (politiques_genre_connaissance : oui/non)
    if is_yes(row.get("politiques_genre_connaissance")):
        points += 1

    # 5) Connaissance GTG (gtg_connaissance : oui/non)
    if is_yes(row.get("gtg_connaissance")):
        points += 1

    return int(round((points/total)*100))

def main():
    csv_path = Path("data/raw/submissions.csv")
    if not csv_path.exists():
        raise SystemExit("CSV introuvable: data/raw/submissions.csv. Lance d’abord 01_fetch_kobo_csv.py")

    # Kobo exports parfois en latin-1 / utf-8; on sécurise
    df = pd.read_csv(csv_path, encoding="utf-8", engine="python", on_bad_lines="skip")
    if df.shape[1] < 5:
        df = pd.read_csv(csv_path, encoding="latin-1", engine="python", on_bad_lines="skip")

    # Colonnes clés (TES en-têtes)
    col_min = "ministere"
    col_sex = "sexe"
    col_fct = "fonction"
    col_form = "formation_genre"
    col_pf_nb = "nb_points_focaux"
    col_cell = "cellule_genre"
    col_plan = "plan_action_genre"
    col_indic = "indicateurs_genre"
    col_budget = "budget_genre_annuel"

    required = [col_min, col_sex, col_fct]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"Colonnes manquantes dans CSV: {missing}")

    # Score
    df["score_connaissance"] = df.apply(compute_score, axis=1)

    # KPI globaux
    total = len(df)
    formes = df[col_form].apply(is_yes).sum() if col_form in df.columns else 0
    score_moy = int(round(pd.to_numeric(df["score_connaissance"], errors="coerce").fillna(0).mean()))

    # % ministères avec point focal (proxy : nb_points_focaux > 0 OU cellule_genre == oui)
    pf_pct = 0
    if col_pf_nb in df.columns or col_cell in df.columns:
        def has_pf(g):
            nb = safe_int(g[col_pf_nb].dropna().astype(str).iloc[0], 0) if col_pf_nb in g.columns and len(g[col_pf_nb].dropna()) else 0
            cell = any(is_yes(x) for x in g[col_cell]) if col_cell in g.columns else False
            return (nb > 0) or cell
        by_min = df.groupby(col_min).apply(has_pf)
        pf_pct = pct(int(by_min.sum()), len(by_min))

    # % intégration politiques (proxy : plan_action_genre==oui OU indicateurs_genre==oui OU budget_genre_annuel>0)
    integ_pct = 0
    def has_integration(g):
        plan = any(is_yes(x) for x in g[col_plan]) if col_plan in g.columns else False
        indic = any(is_yes(x) for x in g[col_indic]) if col_indic in g.columns else False
        bud = any(safe_int(x,0) > 0 for x in g[col_budget]) if col_budget in g.columns else False
        return plan or indic or bud

    by_min2 = df.groupby(col_min).apply(has_integration)
    integ_pct = pct(int(by_min2.sum()), len(by_min2))

    summary = {
        "total_repondants": int(total),
        "pourcentage_formes_genre": int(pct(int(formes), total)),
        "ministeres_avec_point_focal": int(pf_pct),
        "integration_politiques": int(integ_pct),
        "score_moyen_connaissance": int(score_moy),
        "periode_collecte": "",
        "note_methodo": "Export KoboToolbox (CSV) – calcul score sur: compr_genre, diff_sexe_genre, genre_biologique, politiques_genre_connaissance, gtg_connaissance"
    }

    # Agrégats par ministère
    def agg_min(g):
        n = len(g)
        formes_pct = pct(int(g[col_form].apply(is_yes).sum()), n) if col_form in g.columns else 0
        score = int(round(g["score_connaissance"].mean()))
        pf = (safe_int(g[col_pf_nb].dropna().astype(str).iloc[0],0) > 0) if col_pf_nb in g.columns and len(g[col_pf_nb].dropna()) else False
        cell = any(is_yes(x) for x in g[col_cell]) if col_cell in g.columns else False
        pf = pf or cell
        integ = has_integration(g)
        integ_pct_min = 100 if integ else 0  # simplification; on peut raffiner
        return pd.Series({
            "ministere": norm(g[col_min].iloc[0]),
            "formes_genre": formes_pct,
            "point_focal": bool(pf),
            "integration": int(integ_pct_min),
            "score": int(score)
        })

    ministeres = df.groupby(col_min).apply(agg_min).reset_index(drop=True)
    ministeres = ministeres.sort_values("score", ascending=False).to_dict(orient="records")

    # Distributions
    def dist(series):
        s = series.dropna().map(norm)
        out = s.value_counts().reset_index()
        out.columns = ["label", "value"]
        return out.to_dict(orient="records")

    sexe = dist(df[col_sex]) if col_sex in df.columns else []
    fonction = dist(df[col_fct]) if col_fct in df.columns else []

    # Score bins
    scores = pd.to_numeric(df["score_connaissance"], errors="coerce").fillna(0)
    bins = [0,20,40,60,80,100]
    labels = ["0-20","21-40","41-60","61-80","81-100"]
    cats = pd.cut(scores, bins=bins, labels=labels, include_lowest=True, right=True)
    score_bins = cats.value_counts().reindex(labels, fill_value=0).reset_index()
    score_bins.columns = ["label","value"]
    score_bins = score_bins.to_dict(orient="records")

    # Obstacles: ton export a "obstacles" + sous-colonnes "obstacles/obs1..obs8"
    obs_cols = [c for c in df.columns if c.startswith("obstacles/")]
    obstacles = []
    if obs_cols:
        for c in obs_cols:
            obstacles.append({
                "label": c.replace("obstacles/","").upper(),
                "value": int(pd.to_numeric(df[c], errors="coerce").fillna(0).sum())
            })
        obstacles = sorted(obstacles, key=lambda x: x["value"], reverse=True)
    elif "obstacles" in df.columns:
        # fallback: compter tokens dans la chaîne "obs2 obs3 ..."
        from collections import Counter
        cnt = Counter()
        for v in df["obstacles"].dropna().astype(str):
            for tok in v.split():
                cnt[tok.strip()] += 1
        obstacles = [{"label": k.upper(), "value": v} for k,v in cnt.most_common()]

    indicateurs = {
        "sexe": sexe,
        "fonction": fonction,
        "score_bins": score_bins,
        "obstacles": obstacles
    }

    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)

    (out_dir/"summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir/"ministeres.json").write_text(json.dumps(ministeres, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir/"indicateurs.json").write_text(json.dumps(indicateurs, ensure_ascii=False, indent=2), encoding="utf-8")

    print("OK: data/summary.json, data/ministeres.json, data/indicateurs.json mis à jour.")

if __name__ == "__main__":
    main()
