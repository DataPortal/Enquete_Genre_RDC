import os, requests
from pathlib import Path

CANDIDATE_ENDPOINTS = [
    "/api/v2/assets/{asset}/data/?format=csv",
    "/api/v2/assets/{asset}/exports/?format=csv",
]

def main():
    server=os.environ.get("KOBO_SERVER_URL","").rstrip("/")
    token=os.environ.get("KOBO_API_TOKEN","")
    asset=os.environ.get("KOBO_ASSET_ID","")
    if not (server and token and asset):
        raise SystemExit("Missing env vars: KOBO_SERVER_URL, KOBO_API_TOKEN, KOBO_ASSET_ID")

    headers={"Authorization": f"Token {token}"}
    out=Path("data/raw/submissions.csv"); out.parent.mkdir(parents=True, exist_ok=True)

    last=None
    for ep in CANDIDATE_ENDPOINTS:
        url=server+ep.format(asset=asset)
        r=requests.get(url, headers=headers, timeout=180)
        if r.status_code==200 and len(r.content)>10:
            out.write_bytes(r.content)
            print(f"OK: {url} -> {out} ({len(r.content)} bytes)")
            return
        last=f"{url} failed: {r.status_code} {r.text[:200]}"
    raise SystemExit(last or "Download failed")

if __name__=="__main__":
    main()
