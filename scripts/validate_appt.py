import os
#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
PROXY = "http://127.0.0.1:5173"
TUNNEL = "https://playing-caution-divisions-advisors.trycloudflare.com"
AID = int(sys.argv[1]) if len(sys.argv) > 1 else 14


def req(method, path, token=None, body=None, base=BASE):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        try:
            return e.code, json.loads(err)
        except json.JSONDecodeError:
            return e.code, err


def login(email, password):
    _, data = req("POST", "/auth/login-json", None, {"email": email, "password": password})
    return data["access_token"]


def main():
    checks = []
    pat = login("test.patient@example.com", os.environ.get("PILOT_PATIENT_PASSWORD", ""))
    doc = login("dr.mamady@example.com", os.environ.get("PILOT_DOCTOR_PASSWORD", ""))

    print(f"=== VALIDATION RDV #{AID} ===")
    for role, token in [("patient", pat), ("medecin", doc)]:
        for base, label in [(BASE, ":8000"), (PROXY, ":5173")]:
            code, status = req("GET", f"/teleconsultation/appointments/{AID}/room-status", token, base=base)
            ok = code == 200 and status.get("can_join") is True
            checks.append(ok)
            print(
                f"[{'OK' if ok else 'FAIL'}] room-status {role} {label}: "
                f"HTTP {code} can_join={status.get('can_join')} reason={status.get('reason')}"
            )
            code, access = req("GET", f"/teleconsultation/appointments/{AID}/access", token, base=base)
            ok2 = code == 200 and access.get("can_join") is True
            checks.append(ok2)
            print(f"[{'OK' if ok2 else 'FAIL'}] access {role} {label}: HTTP {code} can_join={access.get('can_join')}")
            code, _ = req("GET", f"/appointments/{AID}", token, base=base)
            checks.append(code == 200)
            print(f"[{'OK' if code == 200 else 'FAIL'}] GET /appointments/{AID} {role} {label}: HTTP {code}")

    for base, label in [(PROXY, ":5173"), (TUNNEL, "tunnel")]:
        url = f"{base}/consultation/{AID}"
        with urllib.request.urlopen(urllib.request.Request(url), timeout=20) as resp:
            body = resp.read(200).decode("utf-8", "replace")
        ok = "<!doctype html>" in body.lower()
        checks.append(ok)
        print(f"[{'OK' if ok else 'FAIL'}] Refresh {label}: HTTP {resp.status} HTML={ok}")

    code, bad = req("GET", f"/consultation/{AID}", None, base=BASE)
    print(f"[OK] :8000/consultation/{AID} -> HTTP {code} {bad}")

    _, doc_list = req("GET", "/appointments/", doc)
    _, pat_list = req("GET", "/appointments/", pat)
    vd = any(a.get("id") == AID for a in doc_list)
    vp = any(a.get("id") == AID for a in pat_list)
    checks.extend([vd, vp])
    print(f"[{'OK' if vd else 'FAIL'}] Visible medecin")
    print(f"[{'OK' if vp else 'FAIL'}] Visible patient")

    print("\nLIVRABLES:")
    print(f"APPOINTMENT_ID={AID}")
    print(f"DOCTOR_URL=http://localhost:5173/consultation/{AID}")
    print(f"PATIENT_URL_4G={TUNNEL}/consultation/{AID}")
    print("VERDICT=" + ("GO" if all(checks) else "NO GO"))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
