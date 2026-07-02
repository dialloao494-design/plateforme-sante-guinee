#!/usr/bin/env python3
import httpx, re, sys
F = "https://frontend-seven-rust-94.vercel.app"
html = httpx.get(F + "/", timeout=30).text
m = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
idx = httpx.get(F + m.group(1), timeout=30).text
cm = re.search(r"clinical-pages-[A-Za-z0-9_-]+\.js", idx)
clin = httpx.get(F + "/assets/" + cm.group(0), timeout=60).text
checks = ["Infirmier", "/clinical/nurse", "Signes vitaux", "Enregistrer l", "évaluation", "nurse-his", "nurse-patient-search", "NurseDashboard"]
for c in checks:
    print(c, c in clin)
ok = "nurse-patient-search" in clin or "NurseDashboard" in clin
sys.exit(0 if ok else 1)
