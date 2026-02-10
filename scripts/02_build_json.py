import json
from pathlib import Path
from collections import Counter
import pandas as pd

YES = {"oui","yes","y","true","1","vrai"}
NO  = {"non","no","n","false","0","faux"}

def norm(x):
    if pd.isna(x): return ""
    return str(x).strip()

def is_yes(x): return norm(x).lower() in YES

def pct(n, d):
    return int(round((n / d) * 100)) if d else 0

def fix_mojibake(s: str) -> str:
    """
    Corrige des cas fréquents type 'Ã©' -> 'é' quand un texte UTF-8 a été lu en Latin-1.
    Sans dépendance externe.
    """
    if not s:
        return s
    # heuristique : si présence de 'Ã' ou 'Â', tenter réparation
    if "Ã" in s or "Â" in s:
        try:
            return s.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore").strip()
        except Exception:
            return s
    return s

def decode_csv(path: Path) -> pd.DataFrame:
    # essaie plusieurs encodages
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=enc, engine="python", on_bad_lines="skip")
            if df.shape[1] >= 5:
                return df
        except Exception:
            pass
    # dernier recours
    return pd.read_csv(path, encoding="latin-1", engine="python", on_bad_lines="skip")

def load_meta():
    p = Path("data/meta.json")
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}

def compute_score(row) -> int:
    """
    Score (0–100) basé sur 5 items (pondération simple):
    - compr_genre: bonne=1, moyenne=0.5, faible=0
    - diff_sexe_genre: oui=1
    - genre_biologique: 'FAUX' attendu => 1
    - politiques_genre_connaissance: oui=1
    - gtg_connaissance: oui=1
    """
    points = 0.0
    total = 5.0

    cg = norm(row.get("compr_genre")).lower()
    if cg in {"bonne", "bon", "good"}:
        points += 1
    elif cg in {"moyenne", "average"}:
        points += 0.5

    if is_yes(row.get("diff_sexe_genre")):
        points += 1

    gb = norm(row.get("genre_biologique")).lower()
    # dans tes données: FAUX est la bonne réponse
    if gb in {"faux", "false"}:
        points += 1

    if is_yes(row.get("politiques_genre_connaissance")):
        points += 1

    if is_yes(row.get("gtg_connaissance")):
        points += 1

    return int(round((points / total) * 100))

def build_ministere_label(row, ministere_labels: dict) -> str:
    m = fix_mojibake(norm(row.get("ministere")))
    m_autre = fix_mojibake(norm(row.get("ministere_autre")))
    if m.lower() == "autre" and m_autre:
        m = m_autre
    # mapping optionnel
    return ministere_labels.get(m, m)

def main():
    csv_path = Path("data/raw/submissions.csv")
    if not csv_path.exists():
        raise SystemExit("Missing data/raw/submissions.csv")

    meta = load_meta()
    ministere_labels = meta.get("ministere_labels", {})
    obstacle_labels = meta.get("obstacle_labels", {})  # ex: OBS1..OBS8

    df = decode_csv(csv_path)

    # champs minimum requis
    required = ["ministere", "sexe", "fonction"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    # correction mojibake sur colonnes texte importantes
    text_cols = [c for c in [
        "ministere","ministere_autre","fonction","sexe",
        "importance_justification","recommandations"
    ] if c in df.columns]
    for c in text_cols:
        df[c] = df[c].astype(str).map(fix_mojibake)

    # ministère label propre
    df["_ministere_label"] = df.apply(lambda r: build_ministere_label(r, ministere_labels), axis=1)

    # score connaissance
    df["score_connaissance"] = df.apply(compute_score, axis=1)

    total = len(df)
    formes = df["formation_genre"].apply(is_yes).sum() if "formation_genre" in df.columns else 0
    score_moy = int(round(pd.to_numeric(df["score_connaissance"], errors="coerce").fillna(0).mean())) if total else 0

    # période collecte
    periode = ""
    if "start" in df.columns:
        s = pd.to_datetime(df["start"], errors="coerce").dropna()
        if len(s):
            periode = f"{s.min().date().isoformat()} → {s.max().date().isoformat()}"

    # point focal/cellule (logique robuste)
    def has_pf(g):
        nb = 0
        if "nb_points_focaux" in g.columns:
            nb = int(pd.to_numeric(g["nb_points_focaux"], errors="coerce").fillna(0).max())
        cell = any(is_yes(x) for x in g["cellule_genre"]) if "cellule_genre" in g.columns else False
        return (nb > 0) or cell

    # intégration (plan/indicateurs/budget)
    def has_integration(g):
        plan = any(is_yes(x) for x in g["plan_action_genre"]) if "plan_action_genre" in g.columns else False
        indic = any(is_yes(x) for x in g["indicateurs_genre"]) if "indicateurs_genre" in g.columns else False
        bud = False
        if "budget_genre_annuel" in g.columns:
            bud = any(pd.to_numeric(g["budget_genre_annuel"], errors="coerce").fillna(0) > 0)
        return plan or indic or bud

    by_pf = df.groupby("_ministere_label").apply(has_pf)
    by_int = df.groupby("_ministere_label").apply(has_integration)
    pf_pct = pct(int(by_pf.sum()), len(by_pf))
    int_pct = pct(int(by_int.sum()), len(by_int))

    summary = {
        "total_repondants": int(total),
        "pourcentage_formes_genre": int(pct(int(formes), total)),
        "ministeres_avec_point_focal": int(pf_pct),
        "integration_politiques": int(int_pct),
        "score_moyen_connaissance": int(score_moy),
        "periode_collecte": periode,
        "note_methodo": "Export KoboToolbox (CSV) – pipeline GitHub Actions"
    }

    # agrégation ministères
    def agg_min(g):
        n = len(g)
        formes_pct = pct(int(g["formation_genre"].apply(is_yes).sum()), n) if "formation_genre" in g.columns else 0
        score = int(round(g["score_connaissance"].mean())) if n else 0
        return pd.Series({
            "ministere": norm(g["_ministere_label"].iloc[0]),
            "formes_genre": int(formes_pct),
            "point_focal": bool(has_pf(g)),
            "integration": 100 if has_integration(g) else 0,
            "score": int(score)
        })

    ministeres = (
        df.groupby("_ministere_label").apply(agg_min).reset_index(drop=True)
        .sort_values(["score","formes_genre"], ascending=[False, False])
        .to_dict(orient="records")
    )

    # distributions sexe / fonction
    def dist(col):
        s = df[col].dropna().map(norm)
        vc = s.value_counts().reset_index()
        vc.columns = ["label","value"]
        return vc.to_dict(orient="records")

    indicateurs = {
        "sexe": dist("sexe") if "sexe" in df.columns else [],
        "fonction": dist("fonction") if "fonction" in df.columns else [],
        "score_bins": [],
        "obstacles": []
    }

    # bins score
    scores = pd.to_numeric(df["score_connaissance"], errors="coerce").fillna(0)
    bins = [0,20,40,60,80,100]
    labels = ["0-20","21-40","41-60","61-80","81-100"]
    cats = pd.cut(scores, bins=bins, labels=labels, include_lowest=True, right=True)
    sb = cats.value_counts().reindex(labels, fill_value=0).reset_index()
    sb.columns = ["label","value"]
    indicateurs["score_bins"] = sb.to_dict(orient="records")

    # obstacles : priorité aux colonnes obstacles/obs1..obs8 si présentes
    obs_cols = [c for c in df.columns if c.lower().startswith("obstacles/obs")]
    if obs_cols:
        obs = []
        for c in sorted(obs_cols):
            code = c.split("/")[-1].upper()  # obs1 -> OBS1
            v = int(pd.to_numeric(df[c], errors="coerce").fillna(0).sum())
            label = obstacle_labels.get(code, code)
            obs.append({"label": label, "value": v})
        indicateurs["obstacles"] = sorted(obs, key=lambda x: x["value"], reverse=True)

    elif "obstacles" in df.columns:
        cnt = Counter()
        for v in df["obstacles"].dropna().astype(str):
            for tok in v.split():
                tok = tok.strip().upper()  # obs1 -> OBS1
                if tok:
                    cnt[tok] += 1
        indicateurs["obstacles"] = [{"label": obstacle_labels.get(k,k), "value": v} for k,v in cnt.most_common()]

    # écritures JSON
    Path("data").mkdir(exist_ok=True)
    Path("data/summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("data/ministeres.json").write_text(json.dumps(ministeres, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("data/indicateurs.json").write_text(json.dumps(indicateurs, ensure_ascii=False, indent=2), encoding="utf-8")

    print("OK: data/*.json updated")

if __name__ == "__main__":
    main()
