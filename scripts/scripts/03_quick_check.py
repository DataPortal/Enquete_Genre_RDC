import pandas as pd
from pathlib import Path

def main():
    p=Path("data/raw/submissions.csv")
    if not p.exists(): raise SystemExit("CSV missing: data/raw/submissions.csv")
    try:
        df=pd.read_csv(p, encoding="utf-8", engine="python", on_bad_lines="skip")
        if df.shape[1] < 5: raise UnicodeError("encoding")
    except Exception:
        df=pd.read_csv(p, encoding="latin-1", engine="python", on_bad_lines="skip")
    print("Rows:", len(df))
    print("Cols:", len(df.columns))
    expected=["ministere","sexe","fonction","formation_genre","compr_genre","diff_sexe_genre","genre_biologique","politiques_genre_connaissance","gtg_connaissance"]
    for c in expected:
        print(c, "OK" if c in df.columns else "MISSING")
    print("\nTop missing-rate columns:")
    print(df.isna().mean().sort_values(ascending=False).head(12))

if __name__=="__main__":
    main()
