# Procédure — appel réel PC Windows ↔ iPhone Safari

**Objectif :** médecin et patient dans la **même salle Jitsi**, audio + vidéo **bidirectionnels**, sans popup Google/GitHub, sans `membersOnly`.

**Verdict attendu :** **GO** uniquement si vous vous voyez et vous entendez mutuellement pendant ≥ 1 minute.

---

## Prérequis (une fois)

| Outil | Installation | Vérification |
|-------|--------------|--------------|
| **Docker Desktop** | https://www.docker.com/products/docker-desktop/ | `docker info` sans erreur |
| **cloudflared** | `winget install Cloudflare.cloudflared` **ou** `scripts\tunnel\cloudflared.exe` (déjà dans le repo) | `.\scripts\tunnel\cloudflared.exe --version` |
| **Python 3.12** + **Node.js** | Déjà utilisés pour la plateforme | Backend + Vite démarrent |
| **Comptes pilotes** | Seed actif | Médecin `dr.mamady@example.com` / `[REDACTED — ROTATE IF USED]` — Patient `test.patient@example.com` / `[REDACTED — ROTATE IF USED]` |

> **Ne pas utiliser `meet.jit.si`** — il provoque `membersOnly` et OAuth en iframe.

---

## Vue d’ensemble — 5 terminaux

| # | Rôle | Commande |
|---|------|----------|
| **T1** | Backend API | `.\scripts\qa_start_backend.ps1` |
| **T2** | Frontend app | `cd frontend-sante\frontend` → `npm run dev:tunnel` |
| **T3** | Tunnel **application** (iPhone → Vite) | `.\scripts\tunnel\start-cloudflared.ps1` |
| **T4** | **Jitsi** Docker | `.\scripts\start_jitsi_dev.ps1` |
| **T5** | Tunnel **Jitsi** (iPhone → port 8443) | `.\scripts\tunnel\start-jitsi-cloudflared.ps1` |

Ensuite : appliquer l’URL Jitsi du tunnel T5 dans la config (`apply_jitsi_tunnel_domain.ps1`) et redémarrer T1 + T2.

---

## Étape 1 — Démarrer Jitsi local (T4)

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee
.\scripts\start_jitsi_dev.ps1
```

**Attendu :**
- `docker compose up -d` termine sans erreur
- Dans le navigateur PC : **https://127.0.0.1:8443** — page Jitsi (certificat auto : **Avancé → Continuer** une fois)

**Si Docker manquant :** installer Docker Desktop, le lancer, puis relancer le script.

---

## Étape 2 — Exposer Jitsi via Cloudflare (T5)

**Gardez T4 actif.** Nouveau terminal :

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee
.\scripts\tunnel\start-jitsi-cloudflared.ps1
```

**Attendu :** une ligne du type :

```text
https://something-random.trycloudflare.com
```

**Copiez cette URL** (sans slash final).

### Appliquer le domaine Jitsi partout

Nouveau terminal (ou après Ctrl+C sur T5 si vous avez noté l’URL) :

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee
.\scripts\apply_jitsi_tunnel_domain.ps1 -TunnelUrl "https://VOTRE-URL-JITSI.trycloudflare.com"
```

Cela met à jour `JITSI_DOMAIN` dans `.env` (backend) et `VITE_JITSI_DOMAIN` dans `frontend-sante\frontend\.env.tunnel`.

> **Important :** médecin **et** patient utilisent ce **même** domaine Jitsi (via tunnel), même si le médecin ouvre l’app sur `localhost`.

**Laissez T5 ouvert** pendant tout le test (sinon l’iPhone perd Jitsi).

---

## Étape 3 — Backend + frontend app (T1, T2)

### T1 — Backend

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee
.\scripts\qa_start_backend.ps1
```

Attendu : `Uvicorn running on http://0.0.0.0:8000`

Vérifiez que `.env` contient bien (après étape 2) :

```env
TELECONSULT_PROVIDER=jitsi
JITSI_DOMAIN=votre-url-jitsi.trycloudflare.com
```

### T2 — Frontend (mode tunnel)

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee\frontend-sante\frontend
npm run dev:tunnel
```

Attendu : `Local: http://localhost:5173/`

---

## Étape 4 — Tunnel application pour l’iPhone (T3)

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee
.\scripts\tunnel\start-cloudflared.ps1
```

Copiez l’URL **`https://….trycloudflare.com`** (celle-ci est pour l’**app**, pas Jitsi — souvent **différente** de T5).

| Appareil | URL |
|----------|-----|
| **Médecin (PC)** | `http://localhost:5173/login` |
| **Patient (iPhone Safari)** | `https://XXXX.trycloudflare.com/login` (URL **T3**) |

---

## Étape 5 — Même rendez-vous, même salle

### 5.1 Créer ou utiliser un RDV téléconsultation

- Médecin : dashboard → RDV téléconsultation **confirmé**, dans la fenêtre horaire (ou exécuter le script E2E qui recale un RDV) :

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" scripts\e2e_phase2_embedded_jitsi.py
```

Notez l’`appointment_id` affiché (ex. **15**).

### 5.2 Rejoindre la salle

| Rôle | URL |
|------|-----|
| Médecin PC | `http://localhost:5173/consultation/15` |
| Patient iPhone | `https://XXXX.trycloudflare.com/consultation/15` (même **id**) |

### 5.3 Déroulé côté utilisateur

1. Se connecter (médecin / patient).
2. Sur la page consultation : **autoriser caméra + micro** (Safari : Réglages → Safari → Caméra/Micro pour le site).
3. Cliquer **Rejoindre la salle** (les deux).
4. Attendre **« En direct »** et **2 participants** (ou « Autre participant connecté »).

**À ne pas voir :**
- Popup Google / GitHub
- `membersOnly` / salle d’attente / demande de modérateur
- 0 participant pendant plus de 30 s

---

## Étape 6 — Grille de validation GO / NO GO

| # | Critère | GO | NO GO |
|---|---------|----|-------|
| 1 | Les deux entrent sans OAuth | ☐ | ☐ |
| 2 | Compteur **2 participants** | ☐ | ☐ |
| 3 | **Vidéo** : le médecin voit le patient | ☐ | ☐ |
| 4 | **Vidéo** : le patient voit le médecin | ☐ | ☐ |
| 5 | **Audio** : entendu dans les deux sens | ☐ | ☐ |
| 6 | Stable ≥ **1 minute** | ☐ | ☐ |

**Verdict :**
- **GO** — si et seulement si les 6 lignes sont GO.
- **NO GO** — sinon (noter l’écran exact : erreur, 0 participant, iframe vide, etc.).

---

## Dépannage rapide

| Symptôme | Action |
|----------|--------|
| `membersOnly` | `JITSI_DOMAIN` pointe encore vers `meet.jit.si` → refaire étape 2 |
| Iframe Jitsi vide (PC) | Ouvrir l’URL Jitsi tunnel T5 dans Safari/Chrome ; accepter le certificat si test local 127.0.0.1 |
| iPhone ne charge pas la vidéo | T5 actif ? `apply_jitsi_tunnel_domain` fait ? Redémarrer T1 + T2 |
| 0 participant | Même `appointment_id` ? Même `JITSI_DOMAIN` backend/front ? |
| Safari bloque micro | Réglages iPhone → Safari → Micro/Caméra **Autoriser** pour le domaine tunnel |
| `docker` introuvable | Installer / démarrer Docker Desktop |
| Deux URLs cloudflare | **Normal** : une pour l’app (5173), une pour Jitsi (8443) |

---

## Checklist avant d’appeler Kersor

```text
[ ] T4 Jitsi UP — https://127.0.0.1:8443 répond
[ ] T5 tunnel Jitsi UP — apply_jitsi_tunnel_domain exécuté
[ ] T1 backend redémarré après apply
[ ] T2 Vite redémarré après apply
[ ] T3 tunnel app UP — patient peut se connecter
[ ] Test 1 min PC ↔ iPhone — GO ou NO GO rempli
```

---

## Résumé une page

```powershell
# T4
.\scripts\start_jitsi_dev.ps1

# T5 → copier URL Jitsi
.\scripts\tunnel\start-jitsi-cloudflared.ps1
.\scripts\apply_jitsi_tunnel_domain.ps1 -TunnelUrl "https://JITSI-XXX.trycloudflare.com"

# T1 T2 (redémarrer après apply)
.\scripts\qa_start_backend.ps1
cd frontend-sante\frontend ; npm run dev:tunnel

# T3 → URL app pour iPhone
.\scripts\tunnel\start-cloudflared.ps1

# Médecin : http://localhost:5173/consultation/{id}
# Patient : https://APP-XXX.trycloudflare.com/consultation/{id}
```

**Tant que le test §6 n’est pas GO sur un appel réel, la téléconsultation n’est pas validée.**
