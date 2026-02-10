import os
import sys
import requests
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    raise SystemExit(code)

def normalize_server(url: str) -> str:
    """
    Nettoie KOBO_SERVER_URL:
    - supprime #/forms/... (fragment)
    - supprime tout chemin inutile
    - garde seulement scheme + netloc
    Exemple: https://kf.kobotoolbox.org/#/forms/... -> https://kf.kobotoolbox.org
    """
    url = (url or "").strip()
    if not url:
        return url
    parts = urlsplit(url)
    scheme = parts.scheme or "https"
    netloc = parts.netloc or parts.path  # si l’utilisateur a mis "kf.kobotoolbox.org"
    return urlunsplit((scheme, netloc, "", "", ""))

def try_download(server: str, token: str, asset: str) -> tuple[bool, str]:
    headers = {"Authorization": f"Token {token}"}

    asset_url = f"{server}/api/v2/assets/{asset}/"
    r = requests.get(asset_url, headers=headers, timeout=60)
    if r.status_code != 200:
        return False, f"ASSET {asset_url} -> {r.status_code} {r.text[:120]}"

    csv_url = f"{server}/api/v2/assets/{asset}/data/?format=csv"
    r = requests.get(csv_url, headers=headers, timeout=180)
    if r.status_code != 200:
        return False, f"DATA  {csv_url} -> {r.status_code} {r.text[:120]}"

    out_path = Path("data/raw/submissions.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(r.content)

    if out_path.stat().st_size < 50:
        return False, f"CSV too small ({out_path.stat().st_size} bytes) from {csv_url}"

    return True, f"Downloaded OK from {csv_url} ({out_path.stat().st_size} bytes)"

def main():
    server_raw = os.environ.get("KOBO_SERVER_URL", "")
    token = (os.environ.get("KOBO_API_TOKEN", "") or "").strip()
    asset = (os.environ.get("KOBO_ASSET_ID", "") or "").strip()

    if not token or not asset:
        die("Missing env vars: KOBO_API_TOKEN, KOBO_ASSET_ID (KOBO_SERVER_URL optional)")

    server = normalize_server(server_raw) if server_raw else "https://kf.kobotoolbox.org"

    # Fallback automatique : si 404 sur kf, tester ee (très fréquent)
    candidates = [server]
    if "kf.kobotoolbox.org" in server:
        candidates.append("https://ee.kobotoolbox.org")
    elif "ee.kobotoolbox.org" in server:
        candidates.append("https://kf.kobotoolbox.org")

    last_err = None
    for s in candidates:
        ok, msg = try_download(s, token, asset)
        print(f"[{s}] {msg}")
        if ok:
            return
        last_err = msg

    die("CSV export failed on all candidate servers. Last error: " + (last_err or "unknown"))

if __name__ == "__main__":
    main()
