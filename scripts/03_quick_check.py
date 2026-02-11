from pathlib import Path
import sys
import pandas as pd


def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def read_csv_safely(path: Path) -> pd.DataFrame:
    raw = path.read_bytes()
    if len(raw) < 10:
        die(f"CSV is empty or too small: {path} ({len(raw)} bytes)")

    # Try common encodings (Kobo exports are often utf-8)
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, engine="python", on_bad_lines="skip")
        except Exception:
            pass
    # last resort
    return pd.read_csv(path, engine="python", on_bad_lines="skip")


def main():
    p = Path("data/raw/submissions.csv")
    if not p.exists():
        die("Missing file: data/raw/submissions.csv (did fetch step run?)")

    df = read_csv_safely(p)

    if df.shape[1] == 0:
        die("No columns to parse from CSV. The export may be malformed or empty.")

    # Basic expectations
    must_have = ["consent", "_submission_time"]
    missing = [c for c in must_have if c not in df.columns]
    if missing:
        print("WARNING: missing expected columns:", missing)

    n = len(df)
    n_consent = int((df.get("consent") == "oui").sum()) if "consent" in df.columns else None

    print(f"Rows: {n}")
    if n_consent is not None:
        print(f"Consented rows (consent=='oui'): {n_consent}")

    print("Columns (first 30):", list(df.columns)[:30])


if __name__ == "__main__":
    main()
