import os
import sys
import requests
from pathlib import Path

def die(msg, code=1):
    print(msg, file=sys.stderr)
    raise SystemExit(code)

def main():
    server = (os.environ.get("KOBO_SERVER_URL", "") or "").rstrip("/")
    token  = (os.environ.get("KOBO_API_TOKEN", "") or "").strip()
    asset  = (os.environ.get("KOBO_ASSET_ID", "") or "").strip()

    if not server or not token or not asset:
        die("Missing env vars: KOBO_SERVER_URL, KOBO_API_TOKEN, KOBO_ASSET_ID")

    headers = {"Authorization": f"Token {token}"}

    # 1) Validate asset exists
    asset_url = f"{server}/api/v2/assets/{asset}/"
    r = requests.get(asset_url, headers=headers, timeout=60)
    if r.status_code != 200:
        die(f"Asset validation failed: GET {asset_url} -> {r.status_code} {r.text[:200]}")

    # 2) Download CSV from /data
    csv_url = f"{server}/api/v2/assets/{asset}/data/?format=csv"
    r = requests.get(csv_url, headers=headers, timeout=180)
    if r.status_code != 200:
        die(f"CSV export failed: GET {csv_url} -> {r.status_code} {r.text[:300]}")

    out_path = Path("data/raw/submissions.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(r.content)

    if out_path.stat().st_size < 50:
        die(f"CSV downloaded but looks empty/small ({out_path.stat().st_size} bytes). Check if submissions exist.")

    print(f"Downloaded CSV OK: {csv_url} -> {out_path} ({out_path.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
