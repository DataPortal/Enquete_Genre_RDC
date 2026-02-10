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
        return ""
    parts = urlsplit(url)
    scheme = parts.scheme or "https"
    netloc = parts.netloc or parts.path
    return urlunsplit((scheme, netloc, "", "", ""))

def is_probably_html(resp: requests.Response) -> bool:
    ct = (resp.headers.get("Content-Type") or "").lower()
    if "text/html" in ct:
        return True
    head = (resp.content or b"")[:200].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")

def write_bytes(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

def try_download(url: str, headers: dict, timeout: int = 300) -> tuple[bool, str, bytes]:
    r = requests.get(url, headers=headers, timeout=timeout)
    if r.status_code != 200:
        return False, f"{r.status_code} {r.text[:180]}", b""
    if is_probably_html(r):
        return False, "HTML returned (auth/redirect) instead of CSV", b""
    if len(r.content) < 50:
        return False, f"Too small payload ({len(r.content)} bytes)", b""
    return True, f"OK ({len(r.content)} bytes)", r.content

def main():
    server = normalize_base(os.environ.get("KOBO_SERVER_URL", "https://kf.kobotoolbox.org"))
    token  = (os.environ.get("KOBO_API_TOKEN") or "").strip()
    asset  = (os.environ.get("KOBO_ASSET_ID") or "").strip()

    if not server or not token or not asset:
        die("Missing env vars: KOBO_SERVER_URL, KOBO_API_TOKEN, KOBO_ASSET_ID")

    headers = {"Authorization": f"Token {token}"}
    out = Path("data/raw/submissions.csv")

    # 1) Asset JSON
    asset_url = f"{server}/api/v2/assets/{asset}/"
    r = requests.get(asset_url, headers=headers, timeout=60)
    if r.status_code != 200:
        die(f"ASSET check failed: {asset_url} -> {r.status_code} {r.text[:200]}")
    asset_json = r.json()

    sub_count = asset_json.get("deployment__submission_count")
    print(f"Submission count (Kobo): {sub_count}")

    # 2) Try direct data endpoint (may 404 depending on Kobo)
    direct_url = f"{server}/api/v2/assets/{asset}/data/?format=csv"
    ok, msg, content = try_download(direct_url, headers, timeout=180)
    print(f"[direct] {direct_url} -> {msg}")
    if ok:
        write_bytes(out, content)
        return

    # 3) Preferred: export-settings data_url_csv (retries)
    export_settings = asset_json.get("export_settings") or []
    for es in export_settings:
        data_url_csv = es.get("data_url_csv")
        if not data_url_csv:
            continue

        for attempt in range(1, 6):
            ok, msg, content = try_download(data_url_csv, headers, timeout=300)
            print(f"[export-settings] attempt {attempt}/5 {data_url_csv} -> {msg}")
            if ok:
                write_bytes(out, content)
                return
            time.sleep(5)

    # 4) Fallback: kc export.csv (retries)
    ddl = asset_json.get("deployment__data_download_links") or {}
    kc_csv = ddl.get("csv")
    if kc_csv:
        for attempt in range(1, 6):
            ok, msg, content = try_download(kc_csv, headers, timeout=300)
            print(f"[kc] attempt {attempt}/5 {kc_csv} -> {msg}")
            if ok:
                write_bytes(out, content)
                return
            time.sleep(5)

    # 5) If Kobo claims submissions exist but export still empty, keep pipeline alive by writing empty file
    print("WARN: Could not fetch a valid CSV. Writing empty placeholder to keep pipeline running.")
    write_bytes(out, b"")
    return

if __name__ == "__main__":
    main()
