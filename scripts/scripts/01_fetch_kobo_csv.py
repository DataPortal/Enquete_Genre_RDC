import os
import sys
import requests
from pathlib import Path

"""
Télécharge les soumissions Kobo en CSV.

Requis (env):
- KOBO_SERVER_URL (ex: https://ee.kobotoolbox.org)
- KOBO_API_TOKEN
- KOBO_ASSET_ID (asset uid)

Sortie:
- data/raw/submissions.csv
"""

def main():
    server = os.environ.get("KOBO_SERVER_URL", "").rstrip("/")
    token = os.environ.get("KOBO_API_TOKEN", "")
    asset = os.environ.get("KOBO_ASSET_ID", "")

    if not (server and token and asset):
        raise SystemExit("Missing env vars: KOBO_SERVER_URL, KOBO_API_TOKEN, KOBO_ASSET_ID")

    out_path = Path("data/raw/submissions.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Endpoint Kobo (souvent valide)
    url = f"{server}/api/v2/assets/{asset}/data/?format=csv"

    headers = {"Authorization": f"Token {token}"}

    r = requests.get(url, headers=headers, timeout=180)
    if r.status_code != 200:
        raise SystemExit(f"Download failed: {r.status_code}\n{r.text[:500]}")

    out_path.write_bytes(r.content)
    print(f"OK: saved {out_path} ({len(r.content)} bytes)")

if __name__ == "__main__":
    main()
