from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def looks_like_html(path: Path) -> bool:
    if not path.exists():
        return False
    head = path.read_bytes()[:300].lower()
    return b"<html" in head or b"<!doctype" in head


def read_csv_robust(path: Path) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, engine="python")
        except Exception:
            continue
    return pd.read_csv(path, encoding="latin-1", engine="python", on_bad_lines="skip")


def main() -> None:
    p = Path("data/raw/submissions.csv")
    if not p.exists():
        die("Missing data/raw/submissions.csv (fetch step failed).")

    if p.stat().st_size < 50:
        die(f"CSV file is too small ({p.stat().st_size} bytes). Likely empty export.")

    if looks_like_html(p):
        die("CSV file looks like HTML (wrong endpoint / auth / redirect).")

    df = read_csv_robust(p)

    if df is None or df.empty or len(df.columns) == 0:
        die("CSV parsed but is empty (no rows / no columns).")

    # A very common issue: only header line => df empty
    if len(df) == 0:
        die("CSV has headers but 0 rows. Check if Kobo has submissions / permissions / filters.")

    print("Quick check OK:", {"rows": int(len(df)), "cols": int(len(df.columns))})
    # Useful diagnostics
    cols = set(df.columns.astype(str).tolist())
    print("_submission_time present?", "_submission_time" in cols)
    print("consent present?", "consent" in cols)


if __name__ == "__main__":
    main()
