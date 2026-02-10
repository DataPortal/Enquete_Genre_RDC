from pathlib import Path
import pandas as pd
from pandas.errors import EmptyDataError

def decode_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8", engine="python", on_bad_lines="skip")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", engine="python", on_bad_lines="skip")

def main():
    p = Path("data/raw/submissions.csv")
    if not p.exists():
        print("WARN: submissions.csv missing. Skipping quick check.")
        return

    if p.stat().st_size == 0:
        print("INFO: submissions.csv empty. Skipping quick check.")
        return

    try:
        df = decode_csv(p)
    except EmptyDataError:
        print("INFO: submissions.csv has no columns. Skipping quick check.")
        return

    print(f"Quick check: rows={len(df)} cols={len(df.columns)}")
    if len(df) > 0:
        print("Columns sample:", list(df.columns)[:12])

if __name__ == "__main__":
    main()
