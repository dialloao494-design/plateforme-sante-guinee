# Rapport validation finale — téléconsultation

**Date :** 2026-06-01  
**Verdict global : NO GO** (appel réel PC ↔ iPhone non validé automatiquement)

---

## 1. Infrastructure

| Composant | Statut | Détail |
|-----------|--------|--------|
| Docker Engine | **GO** | 29.5.2, WSL2 actif |
| Jitsi (4 conteneurs) | **GO** | Up ~1h, port **8443** ouvert |
| Tunnel Jitsi | **GO** | `https://mountains-coupons-simon-equal.trycloudflare.com` → HTTP 200 |
| Tunnel app | **PARTIEL** | `https://dot-contains-lodging-chicken.trycloudflare.com` → **502** (Vite arrêté) |
| Backend :8000 | **PARTIEL** | Actif mais `JITSI_DOMAIN=127.0.0.1:8443` (ancien processus) |
| Backend :8001 | **GO** | Actif, `JITSI_DOMAIN` tunnel (convicted-surfing ou mountains selon `.env`) |
| Frontend Vite :5173 | **NO GO** | **Arrêté** — à relancer |
| `JITSI_DOMAIN` fichiers | **GO** | `.env` + `.env.tunnel` alignés sur tunnel Jitsi |
| cloudflared | **GO** | 2 processus actifs |

---

## 2. Parcours automatisé (API)

| Étape | Statut | Détail |
|-------|--------|--------|
| Login médecin / patient | **GO** | `login-json` OK |
| Création RDV téléconsultation | **GO** | RDV **#18** créé par E2E |
| Paiement | **GO** | `confirm-payment` (mode test) |
| Accès salle (API) | **GO** | Même `room_name` patient + médecin |
| `room-status` / `access` | **GO** | Fenêtre join OK |
| Frontend SPA | **NO GO** | Port 5173 fermé |
| Jitsi embed (PC) | **NON TESTÉ** | Dépend Vite + alignement domaine |
| Audio bidirectionnel | **NON TESTÉ** | Humain requis |
| Vidéo bidirectionnelle | **NON TESTÉ** | Humain requis |
| 2 participants | **NON TESTÉ** | Humain requis |
| Stabilité ≥ 1 min | **NON TESTÉ** | Humain requis |

---

## 3. Verdict par critère (votre grille)

| Critère | Verdict |
|---------|---------|
| Médecin voit le patient | **NO GO** |
| Patient voit le médecin | **NO GO** |
| Médecin entend le patient | **NO GO** |
| Patient entend le médecin | **NO GO** |
| Compteur 2 participants | **NO GO** |
| Consultation stable plusieurs minutes | **NO GO** |

---

## 4. Actions humaines obligatoires (3 minutes)

### A — Libérer le port 8000 (recommandé)

Gestionnaire des tâches → fin du processus Python **PID 28932** (accès refusé pour l’agent), ou fermer l’ancien terminal `uvicorn`.

Puis un seul backend :

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee
.\scripts\qa_start_backend.ps1
```

### B — Démarrer le frontend

```powershell
cd frontend-sante\frontend
npm run dev:tunnel
```

Vérifier : `http://localhost:5173` répond.

### C — Relancer le tunnel app si 502

Si `dot-contains-lodging-chicken.trycloudflare.com` renvoie 502 :

```powershell
.\scripts\tunnel\start-cloudflared.ps1
```

Copier la nouvelle URL patient.

### D — Appel réel (seul GO définitif)

| Rôle | URL |
|------|-----|
| Médecin | `http://localhost:5173/consultation/18` |
| Patient iPhone | `https://<URL-tunnel-app>/consultation/18` |

Comptes : `dr.mamady@example.com` / `[REDACTED — ROTATE IF USED]` — `test.patient@example.com` / `[REDACTED — ROTATE IF USED]`

---

## 5. Phase stabilisation (suite)

Prévue après **GO** téléconsultation : documentation, architecture, nettoyage, tests, sécurité, revue ingénierie pour votre frère développeur.

Répondez **« GO appel »** ou **« NO GO appel »** après le test iPhone.
