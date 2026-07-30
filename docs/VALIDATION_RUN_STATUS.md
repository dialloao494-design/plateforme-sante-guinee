# Validation automatique — 2026-06-01

## Automatisé — OK

| Composant | Statut | Détail |
|-----------|--------|--------|
| **Docker** | OK | Engine 29.5.2, WSL2 `docker-desktop` Running |
| **Jitsi** | OK | Conteneurs `docker-jitsi-meet-*` Up, port **8443** ouvert |
| **Tunnel Jitsi** | OK | `https://convicted-surfing-protection-mysterious.trycloudflare.com` → HTTP 200 |
| **Tunnel app** | OK | `https://syndication-auction-aka-mighty.trycloudflare.com` → HTTP 200 |
| **Config fichiers** | OK | `JITSI_DOMAIN` + `VITE_JITSI_DOMAIN` = domaine tunnel Jitsi |
| **Tests unitaires** | OK | `pytest tests/test_teleconsult_access.py` — 9/9 |
| **API salle commune** | OK | RDV **#17**, salle `sante-gn-17-565a95cbaa20` (patient + médecin) |

## Bloquants — action humaine

### 1. Ancien backend sur le port 8000 (priorité)

Deux processus écoutent sur **8000** ; l’un (PID **28932**) n’a pas pu être arrêté (*Accès refusé*) et renvoie encore `jitsi_domain=127.0.0.1:8443`.

**À faire :** fermer le terminal qui exécute l’ancien `uvicorn`, ou Gestionnaire des tâches → fin de processus Python sur le port 8000, puis :

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee
.\scripts\qa_start_backend.ps1
```

Vérifier :

```powershell
$login = Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/login-json" -Method POST -ContentType "application/json" -Body '{"email":"dr.mamady@example.com","password":"[REDACTED — ROTATE IF USED]"}'
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/teleconsultation/appointments/17/access" -Headers @{Authorization="Bearer $($login.access_token)"}).jitsi_domain
```

**Attendu :** `convicted-surfing-protection-mysterious.trycloudflare.com`

### 2. Redémarrer Vite (frontend)

Pour charger `VITE_JITSI_DOMAIN` du tunnel :

```powershell
cd frontend-sante\frontend
npm run dev:tunnel
```

### 3. Appel réel PC ↔ iPhone (seul GO définitif)

| Rôle | URL |
|------|-----|
| Médecin (PC) | `http://localhost:5173/consultation/17` |
| Patient (iPhone Safari) | `https://syndication-auction-aka-mighty.trycloudflare.com/consultation/17` |

Comptes : `dr.mamady@example.com` / `[REDACTED — ROTATE IF USED]` — `test.patient@example.com` / `[REDACTED — ROTATE IF USED]`

**GO** si : 2 participants, vidéo + audio bidirectionnels, stable ≥ 1 min.

**Garder actifs :** tunnels cloudflared (logs dans `logs/jitsi-err.log`, `logs/app-err.log`).

---

## Téléconsultation — verdict actuel

**NO GO** (appel réel non exécuté par l’agent ; backend stale possible sur 8000).

Après correction backend + test iPhone : confirmer **GO** ou **NO GO**.

---

## Phase stabilisation (suite)

Prévue après GO téléconsultation : documentation, architecture, nettoyage, tests, sécurité, revue d’ingénierie.
