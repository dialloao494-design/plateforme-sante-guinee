#!/usr/bin/env python3
"""Wait until Railway nurse API and Vercel nurse UI are both live."""

from __future__ import annotations

import re
import sys
import time

import httpx

BACKEND = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
ADMIN = ("contactpolycliniqueaasma@gmail.com", "AasmaAdmin1!")
TIMEOUT = 900
INTERVAL = 15


def nurse_api_ok() -> bool:
    r = httpx.post(f"{BACKEND}/auth/login-json", json={"email": ADMIN[0], "password": ADMIN[1]}, timeout=45)
    if r.status_code != 200:
        return False
    token = r.json()["access_token"]
    dash = httpx.get(f"{BACKEND}/clinical/nurse/dashboard", headers={"Authorization": f"Bearer {token}"}, timeout=45)
    return dash.status_code == 200


def nurse_frontend_ok() -> bool:
    html = httpx.get(f"{FRONTEND}/", timeout=45, follow_redirects=True).text
    m = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
    if not m:
        return False
    index = httpx.get(f"{FRONTEND}{m.group(1)}", timeout=60).text
    cm = re.search(r"clinical-pages-[A-Za-z0-9_-]+\.js", index)
    if not cm:
        return False
    clinical = httpx.get(f"{FRONTEND}/assets/{cm.group(0)}", timeout=90).text
    return "nurse-patient-search" in clinical or ("Infirmier" in clinical and "Signes vitaux" in clinical and "évaluation" in clinical)


def http_timeout_ok() -> bool:
    html = httpx.get(f"{FRONTEND}/", timeout=45, follow_redirects=True).text
    m = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
    if not m:
        return False
    index = httpx.get(f"{FRONTEND}{m.group(1)}", timeout=60).text
    return "60_000" in index or "60000" in index


def main() -> int:
    deadline = time.time() + TIMEOUT
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        api = nurse_api_ok()
        fe = nurse_frontend_ok()
        timeout = http_timeout_ok()
        print(f"attempt {attempt}: api={api} nurse_ui={fe} timeout_60s={timeout}")
        if api and fe:
            print("Production deploy ready")
            return 0
        time.sleep(INTERVAL)
    print("Timeout waiting for production deploy", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
