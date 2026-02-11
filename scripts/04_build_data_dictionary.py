import json
from pathlib import Path
import pandas as pd


def read_csv_safely(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, engine="python", on_bad_lines="skip")
        except Exception:
            pass
    return pd.read_csv(path, engine="python", on_bad_lines="skip")


def main():
    p = Path("data/raw/submissions.csv")
    df = read_csv_safely(p)

    dic = []
    for c in df.columns:
        example = df[c].dropna().astype(str).head(3).tolist()
        dic.append(
            {
                "name": c,
                "examples": example,
            }
        )

    Path("docs").mkdir(parents=True, exist_ok=True)
    Path("docs/data_dictionary.json").write_text(json.dumps(dic, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote docs/data_dictionary.json")


if __name__ == "__main__":
    main()
