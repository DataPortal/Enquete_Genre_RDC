from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def is_html(content: bytes) -> bool:
    head = content[:300].lower()
    return b"<html" in head or b"<!doctype" in head


def fetch(url: str, token: str, timeout: int = 180) -> requests.Response:
    headers = {"Authorization": f"Token {token}"}
    return requests.get(url, headers=headers, timeout=timeout)


def main() -> None:
    token = (os.getenv("KOBO_API_TOKEN", "") or "").strip()
    kf_url = (os.getenv("KOBO_KF_URL", "") or "").strip().rstrip("/")
    asset = (os.getenv("KOBO_ASSET_ID", "") or "").strip()
    export_uid = (os.getenv("KOBO_EXPORT_SETTING_UID", "") or "").strip()
    kc_username = (os.getenv("KOBO_KC_USERNAME", "") or "").strip()

    if not token or not kf_url or not asset:
        die("Missing env vars: KOBO_API_TOKEN, KOBO_KF_URL, KOBO_ASSET_ID")

    out_path = Path("data/raw/submissions.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    candidates = []

    # 1) Best: export-settings data.csv (exactly what your asset JSON shows)
    if export_uid:
        candidates.append(
            f"{kf_url}/api/v2/assets/{asset}/export-settings/{export_uid}/data.csv"
        )

    # 2) Fallback: Kobo data endpoint (sometimes enabled)
    candidates.append(f"{kf_url}/api/v2/assets/{asset}/data/?format=csv")

    # 3) Fallback: KC report export.csv (needs username)
    # This matches: https://kc.kobotoolbox.org/<username>/reports/<asset>/export.csv
    if kc_username:
        candidates.append(f"https://kc.kobotoolbox.org/{kc_username}/reports/{asset}/export.csv")

    last_err = None

    # Validate asset exists (fast diagnostic)
    asset_url = f"{kf_url}/api/v2/assets/{asset}/"
    r = fetch(asset_url, token, timeout=60)
    if r.status_code != 200:
        die(f"Asset validation failed: GET {asset_url} -> {r.status_code} {r.text[:300]}")

    for url in candidates:
        try:
            r = fetch(url, token, timeout=180)
            if r.status_code != 200:
                last_err = f"{url} -> {r.status_code} {r.text[:200]}"
                continue

            content = r.content or b""
            if len(content) < 50:
                last_err = f"{url} -> 200 but content too small ({len(content)} bytes)"
                continue

            if is_html(content):
                last_err = f"{url} -> 200 but returned HTML (not CSV)."
                continue

            out_path.write_bytes(content)
            print(f"Downloaded CSV OK: {url} -> {out_path} ({out_path.stat().st_size} bytes)")
            return

        except Exception as e:
            last_err = f"{url} -> exception: {e}"

        time.sleep(1)

    die(f"CSV export failed on all candidate URLs. Last error: {last_err}")


if __name__ == "__main__":
    main()
