# Jitsi dédié — téléconsultation embarquée

**Procédure complète test PC ↔ iPhone :** [`docs/TELECONSULT_REAL_CALL_PROCEDURE.md`](../../docs/TELECONSULT_REAL_CALL_PROCEDURE.md)

**Problème :** `meet.jit.si` en iframe provoque `conference.connectionError.membersOnly`, demande OAuth Google/GitHub, lobby/modérateur — **inutilisable en production embarquée**.

**Solution :** instance Jitsi dédiée (Docker local ou JaaS 8x8) sans lobby, sans OAuth, entrée directe médecin/patient authentifiés via l’API plateforme.

---

## Option A — Docker local (dev / pilote LAN)

### Prérequis
- Docker Desktop (Windows/macOS) ou Docker Engine (Linux)
- Ports **8443** (HTTPS) et **8000** (HTTP redirect) libres

### Démarrage rapide

```powershell
.\scripts\start_jitsi_dev.ps1
```

Le script clone [docker-jitsi-meet](https://github.com/jitsi/docker-jitsi-meet) dans `deploy/jitsi/docker-jitsi-meet` (une fois), applique une config sans auth/lobby, puis lance les conteneurs.

### Variables backend (`.env` à la racine)

```env
TELECONSULT_PROVIDER=jitsi
JITSI_DOMAIN=127.0.0.1:8443
# Pas de JITSI_APP_ID requis en mode open (ENABLE_AUTH=0)
```

### Variables frontend (`frontend-sante/frontend/.env.development` ou `.env.tunnel`)

```env
VITE_TELECONSULT_PROVIDER=jitsi
VITE_JITSI_DOMAIN=127.0.0.1:8443
```

Redémarrer FastAPI et Vite après modification.

---

## Option B — Test PC ↔ iPhone (tunnel Cloudflare)

L’iPhone **ne peut pas** joindre `127.0.0.1:8443` sur votre PC. Exposez Jitsi via un second tunnel :

```powershell
cloudflared tunnel --url https://127.0.0.1:8443
```

Copiez l’URL HTTPS affichée (ex. `https://xyz.trycloudflare.com`) et configurez **la même valeur** partout :

```env
# Backend .env
JITSI_DOMAIN=xyz.trycloudflare.com

# Frontend .env.tunnel
VITE_JITSI_DOMAIN=xyz.trycloudflare.com
```

Relancez backend + `npm run dev:tunnel`.

---

## Option C — JaaS 8x8 (production recommandée)

1. Créer un compte sur [jaas.8x8.vc](https://jaas.8x8.vc)
2. Générer une clé API RSA (kid + private key PEM)
3. Configurer :

```env
TELECONSULT_PROVIDER=jitsi
JITSI_JAAS=true
JITSI_APP_ID=vpaas-magic-cookie-xxxxxxxx
JITSI_KEY_ID=vpaas-magic-cookie-xxxxxxxx/yyyyyyyy
JITSI_PRIVATE_KEY_PATH=./secrets/jaas-private.pem
JITSI_DOMAIN=8x8.vc
```

Frontend :

```env
VITE_JITSI_DOMAIN=8x8.vc
```

Le backend émet un JWT RS256 par participant (médecin = modérateur, patient = invité).

---

## Option D — Self-hosted JWT (HS256)

Pour une instance Jitsi Docker avec `AUTH_TYPE=jwt` :

```env
JITSI_DOMAIN=meet.votredomaine.com
JITSI_APP_ID=votre_app_id
JITSI_APP_SECRET=votre_secret_hs256
```

---

## Config serveur appliquée (Option A)

| Paramètre | Valeur | Effet |
|-----------|--------|-------|
| `ENABLE_AUTH` | `0` | Pas de login Google/GitHub |
| `ENABLE_GUESTS` | `1` | Invités autorisés |
| `ENABLE_LOBBY` | `0` | Pas de salle d’attente |
| `ENABLE_PREJOIN_PAGE` | `0` | Entrée directe |
| `ENABLE_WELCOME_PAGE` | `0` | Pas d’écran d’accueil |

---

## Validation

1. Médecin : `http://localhost:5173/consultation/{id}`
2. Patient (tunnel) : `https://…trycloudflare.com/consultation/{id}`
3. Vérifier : **2 participants**, audio + vidéo bidirectionnels, **aucune popup OAuth**

Si `membersOnly` persiste → `JITSI_DOMAIN` pointe encore vers `meet.jit.si` ou le lobby est actif côté serveur.
