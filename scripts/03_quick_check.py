import pandas as pd
from pathlib import Path

def decode_csv(path):
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=enc, engine="python", on_bad_lines="skip")
            if df.shape[1] >= 5:
                return df
        except Exception:
            pass
    return pd.read_csv(path, encoding="latin-1", engine="python", on_bad_lines="skip")

def main():
    p = Path("data/raw/submissions.csv")
    if not p.exists():
        raise SystemExit("CSV missing: data/raw/submissions.csv")

    df = decode_csv(p)
    print("Rows:", len(df))
    print("Cols:", len(df.columns))

    expected = [
        "ministere","ministere_autre","sexe","fonction",
        "formation_genre","compr_genre","diff_sexe_genre","genre_biologique",
        "politiques_genre_connaissance","gtg_connaissance",
        "obstacles","obstacles/obs1","obstacles/obs2","obstacles/obs3","obstacles/obs4",
        "obstacles/obs5","obstacles/obs6","obstacles/obs7","obstacles/obs8"
    ]
    for c in expected:
        print(c, "OK" if c in df.columns else "MISSING")

if __name__ == "__main__":
    main()
