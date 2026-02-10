import pandas as pd
from pathlib import Path

def main():
    p = Path("data/raw/submissions.csv")
    df = pd.read_csv(p, encoding="utf-8", engine="python", on_bad_lines="skip")
    print("Rows:", len(df))
    print("Cols:", len(df.columns))
    for c in ["ministere","sexe","fonction","formation_genre","compr_genre","diff_sexe_genre","genre_biologique","politiques_genre_connaissance","gtg_connaissance"]:
        print(c, "OK" if c in df.columns else "MISSING")

    print("\nMissing values (top columns):")
    na = df.isna().mean().sort_values(ascending=False).head(12)
    print(na)

if __name__ == "__main__":
    main()
