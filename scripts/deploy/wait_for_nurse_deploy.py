#!/usr/bin/env python3
"""Poll production until nurse module is live."""
from __future__ import annotations
import os


import re
import sys
import time

import httpx

BACKEND = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
ADMIN = ("contactpolycliniqueaasma@gmail.com", os.environ["AASMA_ADMIN_PASSWORD"])


def nurse_api_live() -> bool:
    r = httpx.post(f"{BACKEND}/auth/login-json", json={"email": ADMIN[0], "password": ADMIN[1]}, timeout=30)
    if r.status_code != 200:
        return False
    token = r.json()["access_token"]
    dash = httpx.get(f"{BACKEND}/clinical/nurse/dashboard", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    return dash.status_code == 200


def nurse_frontend_live() -> bool:
    html = httpx.get(f"{FRONTEND}/", timeout=30, follow_redirects=True).text
    m = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
    if not m:
        return False
    index = httpx.get(f"{FRONTEND}{m.group(1)}", timeout=60).text
    cm = re.search(r"clinical-pages-[A-Za-z0-9_-]+\.js", index)
    if not cm:
        return False
    clinical = httpx.get(f"{FRONTEND}/assets/{cm.group(0)}", timeout=90).text
    return "Infirmier" in clinical and "Enregistrer l" in clinical and "évaluation" in clinical


def main() -> int:
    for i in range(40):
        api_ok = nurse_api_live()
        fe_ok = nurse_frontend_live() if api_ok else False
        print(f"attempt {i + 1}: api={api_ok} frontend={fe_ok}")
        if api_ok and fe_ok:
            print("Nurse module deployed")
            return 0
        time.sleep(15)
    print("Timeout waiting for nurse deploy", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
