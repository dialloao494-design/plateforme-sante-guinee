# Test multi-appareils en conditions réelles

**Objectif :** médecin sur laptop + patient sur smartphone (Wi‑Fi ou **Orange 4G/5G**), avec création de RDV visible en direct.

---

## Choisir le mode

| Situation | Mode | URL patient |
|-----------|------|-------------|
| Patient sur le **même Wi‑Fi** que le laptop | **LAN** | `http://VOTRE_IP:5173` |
| Patient en **4G/5G Orange** (autre réseau) | **TUNNEL** | `https://xxxx.trycloudflare.com` |

> `localhost` sur le téléphone = le téléphone lui-même, **pas** votre PC. Il faut l’IP LAN ou un tunnel public.

---

## Mode TUNNEL (recommandé — 4G + Wi‑Fi)

Une seule base de données sur votre laptop ; le patient passe par Internet via Cloudflare.

### Prérequis

- Python 3.12 + Node.js installés
- [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) : `winget install Cloudflare.cloudflared`

### Étape 0 — Aperçu

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee
.\scripts\start_remote_test.ps1 -Mode tunnel
```

### Terminal 1 — Backend

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee
.\scripts\qa_start_backend.ps1
```

Attendu : `Uvicorn running on http://0.0.0.0:8000`

### Terminal 2 — Frontend (proxy API intégré)

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee\frontend-sante\frontend
npm run dev:tunnel
```

Attendu : `Local: http://localhost:5173/` — les appels API passent par le proxy Vite → port 8000.

### Terminal 3 — URL publique pour le téléphone

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee
.\scripts\tunnel\start-cloudflared.ps1
```

Copiez l’URL **`https://….trycloudflare.com`** affichée.

| Qui | URL à ouvrir |
|-----|----------------|
| **Patient (téléphone)** | `https://XXXX.trycloudflare.com/login` |
| **Médecin (laptop)** | `http://localhost:5173/login` |

Les deux utilisent la **même** instance backend sur votre PC.

### Ports exposés

| Port | Exposé Internet ? | Rôle |
|------|-------------------|------|
| **8000** | Non (local) | API FastAPI |
| **5173** | Via cloudflared uniquement | React + proxy API |
| **443** | Sortant (tunnel) | HTTPS public temporaire |

Aucune ouverture de port sur la box n’est nécessaire en mode tunnel.

---

## Mode LAN (même Wi‑Fi uniquement)

### Terminal 1 — Backend LAN

```powershell
.\scripts\qa_start_backend.ps1
# ou: .\scripts\run_local_backend.ps1 -Lan
```

### Terminal 2 — Frontend LAN

```powershell
.\scripts\qa_start_frontend.ps1
# ou: cd frontend-sante\frontend; npm run dev:lan
```

### Firewall Windows (si le téléphone ne charge pas)

PowerShell **Administrateur** :

```powershell
.\scripts\open_firewall_lan.ps1
```

### URLs

```powershell
.\scripts\print_lan_urls.ps1
```

Exemple :

- **Laptop médecin :** `http://localhost:5173/doctor/dashboard`
- **Téléphone patient :** `http://172.20.10.2:5173/login` (remplacez par votre IP affichée)

### Vérification automatique

```powershell
.\scripts\qa_verify_lan.ps1
```

---

## Comptes de test

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Médecin | `dr.mamady@example.com` | `Doctor123!` |
| Médecin (alt.) | `dr.amu@example.com` | `Doctor123!` |
| Patient existant | `test.patient@example.com` | `Patient123!` |

Le patient peut aussi **s’inscrire** via `/signup` (nouveau compte).

### Réinitialiser les RDV (optionnel)

```powershell
python scripts\reset_qa_lab.py
```

Garde les comptes pilotes, efface rendez-vous / messages / notifications.

---

## Scénario de test pas à pas

### Médecin (laptop)

1. Ouvrir `http://localhost:5173/login` (tunnel) ou LAN.
2. Se connecter : `dr.mamady@example.com` / `Doctor123!`
3. Aller sur **Tableau de bord médecin** → **Rendez-vous** (`/doctor/appointments`).
4. Laisser l’onglet ouvert (rafraîchir si besoin).

### Patient (téléphone)

1. Ouvrir l’URL tunnel **`https://….trycloudflare.com`** ou LAN `http://IP:5173`.
2. **S’inscrire** (`/signup`) *ou* se connecter avec `test.patient@example.com` / `Patient123!`
3. **Médecins** → choisir un médecin → prendre un créneau / RDV.
4. Confirmer le rendez-vous (paiement test si demandé).

### Médecin — validation

1. Rafraîchir **Rendez-vous** : le nouveau RDV doit apparaître.
2. Optionnel : ouvrir la fiche patient / messages.

---

## Dépannage

| Symptôme | Solution |
|----------|----------|
| « Impossible de joindre l’API » sur téléphone | Backend terminal 1 actif ; en tunnel utiliser `npm run dev:tunnel` (pas `dev` seul) |
| Page blanche sur téléphone (LAN) | Firewall : `open_firewall_lan.ps1` ; même Wi‑Fi ; IP correcte |
| 4G ne peut pas joindre `http://192.168.x.x` | Normal → utiliser **mode TUNNEL** |
| CORS / erreur réseau en tunnel | Relancer `dev:tunnel` + cloudflared |
| Login incorrect | `Doctor123!` / `Patient123!` exactement |

---

## Sécurité (temporaire)

- Tunnel Cloudflare = **public** pendant le test ; ne pas partager l’URL largement.
- Arrêter cloudflared + Ctrl+C sur les serveurs après le test.
- Ne pas utiliser de vraies données médicales sensibles en QA.

---

## Alternative : ngrok

```powershell
ngrok http 5173
```

Utilisez l’URL `https://….ngrok-free.app` sur le téléphone. Gardez `npm run dev:tunnel` pour le proxy API.
