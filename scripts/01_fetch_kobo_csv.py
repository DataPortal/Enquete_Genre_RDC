import os
import sys
import time
from pathlib import Path
import requests


def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def get_env(name: str, required: bool = True) -> str:
    v = (os.environ.get(name, "") or "").strip()
    if required and not v:
        return ""
    return v


def http_get(url: str, headers: dict, timeout: int = 120) -> requests.Response:
    return requests.get(url, headers=headers, timeout=timeout)


def pick_export_setting_uid(kf_url: str, asset_id: str, headers: dict) -> str:
    """
    If KOBO_EXPORT_SETTING_UID is not provided, we list export-settings and pick the first.
    """
    url = f"{kf_url}/api/v2/assets/{asset_id}/export-settings/"
    r = http_get(url, headers=headers, timeout=60)
    if r.status_code != 200:
        die(f"Cannot list export-settings: GET {url} -> {r.status_code} {r.text[:250]}")
    data = r.json()
    results = data.get("results", []) if isinstance(data, dict) else []
    if not results:
        die(
            "No export-settings found. In Kobo UI, create an export setting for CSV "
            "(include all versions) then retry."
        )
    uid = results[0].get("uid", "")
    if not uid:
        die("export-settings response did not include uid.")
    return uid


def download_csv_via_export_setting(kf_url: str, asset_id: str, export_uid: str, headers: dict) -> bytes:
    """
    Primary method: export-settings/<uid>/data.csv
    """
    url = f"{kf_url}/api/v2/assets/{asset_id}/export-settings/{export_uid}/data.csv"
    r = http_get(url, headers=headers, timeout=180)
    if r.status_code == 200 and len(r.content) > 0:
        return r.content

    # Sometimes Kobo returns 202 while preparing; retry briefly.
    if r.status_code in (202, 201):
        for _ in range(10):
            time.sleep(3)
            r2 = http_get(url, headers=headers, timeout=180)
            if r2.status_code == 200 and len(r2.content) > 0:
                return r2.content

    die(f"CSV export failed: GET {url} -> {r.status_code} {r.text[:300]}")
    return b""


def main():
    kf_url = get_env("KOBO_KF_URL", required=True)
    asset_id = get_env("KOBO_ASSET_ID", required=True)
    token = get_env("KOBO_API_TOKEN", required=True)
    export_uid = get_env("KOBO_EXPORT_SETTING_UID", required=False)

    missing = []
    if not token:
        missing.append("KOBO_API_TOKEN")
    if not kf_url:
        missing.append("KOBO_KF_URL")
    if not asset_id:
        missing.append("KOBO_ASSET_ID")

    if missing:
        die("Missing env vars: " + ", ".join(missing))

    kf_url = kf_url.rstrip("/")
    headers = {"Authorization": f"Token {token}"}

    # Validate asset exists
    asset_url = f"{kf_url}/api/v2/assets/{asset_id}/"
    r = http_get(asset_url, headers=headers, timeout=60)
    if r.status_code != 200:
        die(f"Asset validation failed: GET {asset_url} -> {r.status_code} {r.text[:250]}")

    # Determine export setting uid
    if not export_uid:
        export_uid = pick_export_setting_uid(kf_url, asset_id, headers)

    csv_bytes = download_csv_via_export_setting(kf_url, asset_id, export_uid, headers)

    out_path = Path("data/raw/submissions.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write as-is
    out_path.write_bytes(csv_bytes)

    # Minimal sanity check
    if out_path.stat().st_size < 20:
        die(f"CSV downloaded but too small ({out_path.stat().st_size} bytes). Check if submissions exist.")

    print(f"Downloaded CSV OK -> {out_path} ({out_path.stat().st_size} bytes)")
    print(f"Source: {kf_url}/api/v2/assets/{asset_id}/export-settings/{export_uid}/data.csv")


if __name__ == "__main__":
    main()
