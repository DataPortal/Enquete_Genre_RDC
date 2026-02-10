import os
import sys
import time
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

def is_probably_html(resp: requests.Response) -> bool:
    ct = (resp.headers.get("Content-Type") or "").lower()
    if "text/html" in ct:
        return True
    # fallback: check first bytes
    head = (resp.content or b"")[:200].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")

def write_bytes(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

def try_download_csv(url: str, headers: dict, out: Path, timeout: int = 300) -> tuple[bool, str]:
    r = requests.get(url, headers=headers, timeout=timeout)
    if r.status_code != 200:
        return False, f"{r.status_code} {r.text[:140]}"
    if is_probably_html(r):
        return False, "Got HTML (likely auth/redirect) instead of CSV"
    if len(r.content) < 50:
        return False, f"Too small payload ({len(r.content)} bytes)"
    write_bytes(out, r.content)
    return True, f"OK ({len(r.content)} bytes)"

def main():
    server = normalize_base(os.environ.get("KOBO_SERVER_URL", "https://kf.kobotoolbox.org"))
    token  = (os.environ.get("KOBO_API_TOKEN") or "").strip()
    asset  = (os.environ.get("KOBO_ASSET_ID") or "").strip()

    if not token or not asset:
        die("Missing env vars: KOBO_API_TOKEN, KOBO_ASSET_ID")

    headers = {"Authorization": f"Token {token}"}
    out = Path("data/raw/submissions.csv")

    # 1) Check asset
    asset_url = f"{server}/api/v2/assets/{asset}/"
    r = requests.get(asset_url, headers=headers, timeout=60)
    if r.status_code != 200:
        die(f"ASSET check failed: {asset_url} -> {r.status_code} {r.text[:200]}")
    asset_json = r.json()

    # If no submissions, create an empty CSV with headers (optional)
    sub_count = asset_json.get("deployment__submission_count")
    print(f"Submission count (Kobo): {sub_count}")
    if isinstance(sub_count, int) and sub_count == 0:
        # Create a minimal CSV to avoid pandas crash downstream
        write_bytes(out, b"")
        print("No submissions yet. Wrote empty CSV placeholder.")
        return

    # 2) Direct endpoint (may 404)
    direct_csv = f"{server}/api/v2/assets/{asset}/data/?format=csv"
    ok, msg = try_download_csv(direct_csv, headers, out)
    print(f"[direct] {direct_csv} -> {msg}")
    if ok:
        return

    # 3) export-settings data_url_csv (best for your case)
    export_settings = asset_json.get("export_settings") or []
    for es in export_settings:
        data_url_csv = es.get("data_url_csv")
        if not data_url_csv:
            continue

        # retry a few times because sometimes export-settings returns empty while generating
        for attempt in range(1, 6):
            ok, msg = try_download_csv(data_url_csv, headers, out)
            print(f"[export-settings] attempt {attempt}/5 {data_url_csv} -> {msg}")
            if ok:
                return
            time.sleep(5)

    # 4) Fallback: kc report link
    ddl = (asset_json.get("deployment__data_download_links") or {})
    kc_csv = ddl.get("csv")
    if kc_csv:
        for attempt in range(1, 6):
            ok, msg = try_download_csv(kc_csv, headers, out)
            print(f"[kc] attempt {attempt}/5 {kc_csv} -> {msg}")
            if ok:
                return
            time.sleep(5)

    # If we got here, everything failed
    die(
        "CSV download failed via all methods.\n"
        f"- direct: {direct_csv}\n"
        f"- export_settings tried: {len(export_settings)}\n"
        f"- kc_csv present: {bool(kc_csv)}\n"
        "Most likely causes: token lacks view_submissions, or returned HTML/empty export."
    )

if __name__ == "__main__":
    main()
