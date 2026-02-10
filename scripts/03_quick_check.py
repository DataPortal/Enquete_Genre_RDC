import sys
from pathlib import Path
import pandas as pd
from pandas.errors import EmptyDataError

def decode_csv(path: Path) -> pd.DataFrame:
    # Kobo exports sometimes include accents; try utf-8 first, fallback latin-1
    try:
        return pd.read_csv(path, encoding="utf-8", engine="python", on_bad_lines="skip")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", engine="python", on_bad_lines="skip")

def main():
    p = Path("data/raw/submissions.csv")
    if not p.exists():
        print("WARN: data/raw/submissions.csv not found. Skipping checks.")
        return

    if p.stat().st_size == 0:
        print("INFO: submissions.csv is empty (0 bytes). No submissions yet or export empty. Skipping checks.")
        return

    try:
        df = decode_csv(p)
    except EmptyDataError:
        print("INFO: submissions.csv has no columns to parse. Skipping checks.")
        return

    print(f"Rows: {len(df)} | Cols: {len(df.columns)}")
    if len(df) == 0:
        print("INFO: CSV parsed but contains 0 rows. OK.")
        return

    # minimal sanity checks
    must_have = ["_submission_time", "_id", "_uuid"]
    missing = [c for c in must_have if c not in df.columns]
    if missing:
        print(f"WARN: missing expected columns: {missing}")

if __name__ == "__main__":
    main()
