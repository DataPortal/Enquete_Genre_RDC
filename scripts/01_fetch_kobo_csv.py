import os
import sys
import requests
from pathlib import Path

def fail(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    raise SystemExit(code)

def main():
    server = (os.environ.get("KOBO_SERVER_URL", "") or "").rstrip("/")
    token  = (os.environ.get("KOBO_API_TOKEN", "") or "").strip()
    asset  = (os.environ.get("KOBO_ASSET_ID", "") or "").strip()

    if not server or not token or not asset:
        fail("Missing env vars: KOBO_SERVER_URL, KOBO_API_TOKEN, KOBO_ASSET_ID")

    headers = {"Authorization": f"Token {token}"}
    out_path = Path("data/raw/submissions.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) Validate asset exists
    asset_url = f"{server}/api/v2/assets/{asset}/"
    r = requests.get(asset_url, headers=headers, timeout=60)
    if r.status_code == 404:
        fail(
            "KOBO_ASSET_ID invalide OU mauvais serveur.\n"
            f"- Vérifie que KOBO_SERVER_URL est correct (ex: https://ee.kobotoolbox.org ou https://kf.kobotoolbox.org)\n"
            "- Vérifie que KOBO_ASSET_ID est l'UID de l'asset (souvent commence par 'a...'), pas un ID numérique.\n"
            f"- Testé: GET {asset_url} -> 404"
        )
    if r.status_code != 200:
        fail(f"Impossible de valider l'asset: GET {asset_url} -> {r.status_code} {r.text[:200]}")

    # 2) Download CSV via standard endpoint (most Kobo deployments)
    data_csv_url = f"{server}/api/v2/assets/{asset}/data/?format=csv"
    r = requests.get(data_csv_url, headers=headers, timeout=180)
    if r.status_code == 200 and len(r.content) > 50:
        out_path.write_bytes(r.content)
        print(f"Downloaded CSV: {data_csv_url} -> {out_path} ({len(r.content)} bytes)")
        return

    # 3) If fails, print detailed diagnostic
    fail(
        "Échec export CSV via endpoint standard.\n"
        f"- URL testée: {data_csv_url}\n"
        f"- Status: {r.status_code}\n"
        f"- Réponse: {r.text[:300]}\n"
        "\nPistes:\n"
        "1) Ton token n'a peut-être pas accès à cet asset.\n"
        "2) Ton instance Kobo peut exiger un export différent (plus rare).\n"
        "3) L’asset existe mais n’a pas de soumissions (CSV vide/erreur).\n"
    )

if __name__ == "__main__":
    main()
