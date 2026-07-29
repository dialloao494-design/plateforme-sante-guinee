#!/usr/bin/env python3
import os
import httpx

BASE = "https://web-production-ad6a36.up.railway.app"


def login(email, password):
    r = httpx.post(
        f"{BASE}/auth/login-json",
        json={"email": email, "password": password},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    recep_token = login("baldoumar14@gmail.com", os.environ["AASMA_RECEPTION_PASSWORD"])
    lab_token = login("mamadoudianbarry06@gmail.com", os.environ["AASMA_LAB_PASSWORD"])
    h_recep = {"Authorization": f"Bearer {recep_token}"}
    h_lab = {"Authorization": f"Bearer {lab_token}"}

    tests = [
        ("GET", "/clinical/workflow/queue/reception", h_recep, None),
        ("GET", "/clinical/workflow/queue/lab", h_lab, None),
        ("GET", "/clinical/lab/orders", h_lab, None),
        ("GET", "/clinical/reception/patients?q=test", h_recep, None),
        ("POST", "/clinical/reception/patients", h_recep, {
            "first_name": "Probe",
            "last_name": "API",
            "age": 28,
            "gender": "F",
            "phone": "620991122",
            "mother_name": "Fatou Probe",
            "visit_destination": "Laboratoire",
            "quartier": "Ratoma",
            "profession": "Commerçante",
        }),
    ]
    for method, path, headers, body in tests:
        if method == "GET":
            r = httpx.get(f"{BASE}{path}", headers=headers, timeout=60)
        else:
            r = httpx.post(f"{BASE}{path}", headers=headers, json=body, timeout=60)
        print(f"\n{method} {path} -> {r.status_code}")
        print(r.text[:500])


if __name__ == "__main__":
    main()
