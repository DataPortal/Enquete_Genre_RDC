import os
import sys
import requests
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    raise SystemExit(code)

def normalize_base(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return url
    parts = urlsplit(url)
    scheme = parts.scheme or "https"
    netloc = parts.netloc or parts.path
    return urlunsplit((scheme, netloc, "", "", ""))

def http_get(url: str, headers: dict, timeout: int = 180) -> requests.Response:
    return requests.get(url, headers=headers, timeout=timeout)

def main():
    server = normalize_base(os.environ.get("KOBO_SERVER_URL", "https://kf.kobotoolbox.org"))
    token  = (os.environ.get("KOBO_API_TOKEN") or "").strip()
    asset  = (os.environ.get("KOBO_ASSET_ID") or "").strip()

    if not token or not asset:
        die("Missing env vars: KOBO_API_TOKEN, KOBO_ASSET_ID (KOBO_SERVER_URL optional)")

    headers = {"Authorization": f"Token {token}"}

    out = Path("data/raw/submissions.csv")
    out.parent.mkdir(parents=True, exist_ok=True)

    # 1) Asset JSON
    asset_url = f"{server}/api/v2/assets/{asset}/"
    r = http_get(asset_url, headers, timeout=60)
    if r.status_code != 200:
        die(f"ASSET check failed: {asset_url} -> {r.status_code} {r.text[:300]}")

    asset_json = r.json()

    # 2) Try direct data endpoint (may 404 on some Kobo configs)
    direct_csv_url = f"{server}/api/v2/assets/{asset}/data/?format=csv"
    r = http_get(direct_csv_url, headers, timeout=180)
    if r.status_code == 200 and len(r.content) > 50:
        out.write_bytes(r.content)
        print(f"OK (direct): {direct_csv_url} -> {out} ({out.stat().st_size} bytes)")
        return
    else:
        print(f"Direct CSV not available: {direct_csv_url} -> {r.status_code}")

    # 3) Preferred: export-settings data_url_csv
    export_settings = asset_json.get("export_settings") or []
    for es in export_settings:
        data_url_csv = es.get("data_url_csv")
        if not data_url_csv:
            continue
        r = http_get(data_url_csv, headers, timeout=300)
        if r.status_code == 200 and len(r.content) > 50:
            out.write_bytes(r.content)
            print(f"OK (export-settings): {data_url_csv} -> {out} ({out.stat().st_size} bytes)")
            return
        else:
            print(f"Export-settings CSV failed: {data_url_csv} -> {r.status_code} {r.text[:120]}")

    # 4) Fallback: deployment__data_download_links.csv (kc)
    ddl = (asset_json.get("deployment__data_download_links") or {})
    kc_csv = ddl.get("csv")
    if kc_csv:
        r = http_get(kc_csv, headers, timeout=300)
        if r.status_code == 200 and len(r.content) > 50:
            out.write_bytes(r.content)
            print(f"OK (kc fallback): {kc_csv} -> {out} ({out.stat().st_size} bytes)")
            return
        else:
            print(f"KC CSV failed: {kc_csv} -> {r.status_code} {r.text[:120]}")

    die(
        "CSV export failed via all methods.\n"
        f"- direct: {direct_csv_url}\n"
        f"- export-settings tried: {len(export_settings)}\n"
        f"- kc link present: {bool(kc_csv)}\n"
        "Check that KOBO_API_TOKEN has 'view_submissions' permission and that submissions exist."
    )

if __name__ == "__main__":
    main()
