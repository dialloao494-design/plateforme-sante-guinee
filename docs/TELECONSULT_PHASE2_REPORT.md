# Rapport Phase 2 — Téléconsultation Jitsi embarquée

**Date :** 2026-06-01  
**Verdict automatisé :** **GO** (API + build)  
**Verdict vidéo PC ↔ iPhone (manuel) :** **NO GO tant que meet.jit.si** — migrer vers Jitsi dédié (voir §6)

---

## 1. Fichiers modifiés / créés

### Backend
| Fichier | Action |
|---------|--------|
| `services/teleconsult_room.py` | **Créé** — nom de salle hashé + URL Jitsi |
| `services/teleconsultation_access.py` | **Modifié** — provider `jitsi` effectif, payload embed enrichi |
| `services/rendezvous_service.py` | **Modifié** — `meeting_link` unifié à la création |
| `routers/teleconsultation.py` | **Modifié** — config provider `jitsi` par défaut |
| `tests/test_teleconsult_access.py` | **Modifié** — +2 tests embed |
| `scripts/migrate_meeting_links.py` | **Créé** — migration liens existants |
| `scripts/e2e_phase2_embedded_jitsi.py` | **Créé** — validation Phase 2 |

### Frontend
| Fichier | Action |
|---------|--------|
| `package.json` / `package-lock.json` | **Modifié** — `@jitsi/react-sdk@1.4.4` |
| `src/components/JitsiEmbeddedMeeting.jsx` | **Créé** — iframe Jitsi + events participants |
| `src/pages/ConsultationRoom.jsx` | **Refactor** — stub vidéo supprimé, embed natif |
| `src/pages/ConsultationRoom.css` | **Modifié** — conteneur Jitsi responsive |
| `src/services/teleconsultationProvider.js` | **Modifié** — embed helpers + erreurs media FR |
| `src/pages/TeleconsultationHub.jsx` | **Modifié** — copy « salle intégrée » |
| `.env.tunnel` / `.env.example` | **Modifié** — `VITE_TELECONSULT_PROVIDER=jitsi` |

### Supprimé du parcours utilisateur
- `window.open()` pour Jitsi dans `ConsultationRoom.jsx`
- Timers simulés « connexion / pair connecté »
- Placeholder « Flux principal (SDK à intégrer) »

---

## 2. Architecture retenue

```
Patient/Médecin → ConsultationRoom (prejoin + probe getUserMedia)
                → GET /teleconsultation/appointments/{id}/access  (RBAC + fenêtre)
                → JitsiEmbeddedMeeting (@jitsi/react-sdk → iframe meet.jit.si)
                → WebRTC audio/vidéo (géré par Jitsi, in-app)
                → POST /teleconsultation/appointments/{id}/end
```

- **Contrôle d'accès :** inchangé (`room-status`, `access`, RBAC patient/médecin).
- **Identifiant de salle unique :** `sante-gn-{id}-{hash12}` via `/access` (source de vérité pour l'embed).
- **Pas de WebRTC maison :** ICE/STUN/TURN délégués à Jitsi public (`meet.jit.si`).

---

## 3. Tests automatisés exécutés

| Test | Résultat |
|------|----------|
| `pytest tests/test_teleconsult_access.py` (8 tests) | **PASS** |
| `npm run build` (Vite production) | **PASS** |
| `scripts/e2e_phase2_embedded_jitsi.py` | **GO** |

### Logs E2E (extrait)
```
[OK] access patient: sante-gn-15-2915f5046f13 domain=meet.jit.si
[OK] access doctor:  sante-gn-15-2915f5046f13 domain=meet.jit.si
[OK] SPA :5173/consultation/15
[OK] SPA tunnel/consultation/15
VERDICT=GO
```

**RDV de test actif :** `#15` (fenêtre join recalée automatiquement par le script).

---

## 4. URLs exactes à tester

| Rôle | URL |
|------|-----|
| **Médecin (PC)** | `http://localhost:5173/consultation/15` |
| **Patient (iPhone 4G)** | `https://playing-caution-divisions-advisors.trycloudflare.com/consultation/15` |
| Login médecin | `http://localhost:5173/login` → **Médecin démo** |
| Login patient | tunnel `/login` → **Patient démo** |

**Comptes :** `dr.mamady@example.com` / `[REDACTED — ROTATE IF USED]` · `test.patient@example.com` / `[REDACTED — ROTATE IF USED]`

---

## 5. Protocole de validation médecin ↔ patient

### Prérequis (3 terminaux)
1. Backend : `uvicorn main:app --host 127.0.0.1 --port 8000`
2. Frontend : `npm run dev:tunnel` (dans `frontend-sante/frontend`)
3. Tunnel : `cloudflared` → URL `*.trycloudflare.com`

### Étapes
1. **Médecin (PC)** : login → ouvrir `http://localhost:5173/consultation/15`
2. **Patient (iPhone Safari)** : login via tunnel → `/consultation/15`
3. Les deux : autoriser **caméra + micro** au prejoin
4. Les deux : cliquer **« Rejoindre la consultation »**
5. Vérifier :
   - Vidéo intégrée **dans la page** (pas de nouvel onglet)
   - Compteur **« 2 participants »** quand les deux sont connectés
   - Statut **« Patient connecté »** / **« Médecin en ligne »**
   - Audio bidirectionnel (parler / écouter)
   - Micro/cam via toolbar Jitsi dans l'iframe
6. **Médecin** : **« Quitter la consultation »** → écran « Consultation terminée »
7. **Refresh F5** sur `:5173/consultation/15` → SPA recharge (pas de JSON `Introuvable`)

### Safari iPhone — permissions
Réglages → Safari → Caméra / Micro → **Autoriser** pour le domaine tunnel.  
Si refus : message rouge explicite dans la bannière prejoin.

---

## 6. Correctif bug bloquant `membersOnly` (2026-06-01)

| Symptôme | Cause | Correctif livré |
|----------|-------|-----------------|
| `conference.connectionError.membersOnly` | `meet.jit.si` exige OAuth (Google/GitHub) pour le créateur de salle en iframe | **Interdit** comme domaine embed ; défaut → `127.0.0.1:8443` (Jitsi Docker) |
| 0 participant, popup OAuth | Lobby/modérateur sur instance publique | Config serveur : `ENABLE_AUTH=0`, `ENABLE_LOBBY=0` (`deploy/jitsi/`) |
| Safari bloque popup | Login tiers dans iframe | `disableLogin`, pas d’OAuth sur instance dédiée |

**Actions requises pour valider PC ↔ iPhone :**
1. `.\scripts\start_jitsi_dev.ps1` (ou JaaS 8x8 en prod)
2. Tunnel Cloudflare sur le port **8443** Jitsi (voir `deploy/jitsi/README.md`)
3. `JITSI_DOMAIN` + `VITE_JITSI_DOMAIN` = URL tunnel Jitsi (pas `meet.jit.si`)
4. Re-tester RDV #15 médecin PC + patient iPhone Safari

---

## 7. Limitations restantes (Phase 3)

| Limitation | Détail |
|------------|--------|
| **Jitsi public** | `meet.jit.si` — pas de JWT, salles non privées au sens strict |
| **Toolbar Jitsi** | Contrôles micro/cam dans l'iframe Jitsi (pas custom UI plateforme) |
| **Partage d'écran** | Non activé (Phase 3) |
| **Enregistrement** | Non implémenté |
| **Chat in-call** | Messagerie REST séparée (`/messages/{id}`) |
| **Synthèse médecin** | Toujours `localStorage` |
| **Migration DB** | `meeting_link` migré ; l'embed utilise toujours `room_name` de `/access` |
| **Charge meet.jit.si** | Service public — pour prod clinique → 8x8 JaaS ou Jitsi self-hosted + JWT |

---

## 8. Verdict final

| Critère | Statut |
|---------|--------|
| Plus d'onglet Jitsi externe | **GO** (code) |
| SDK embarqué in-app | **GO** (build + composant) |
| API accès + même salle patient/médecin | **GO** (E2E) |
| Join / quit / participants / erreurs media | **GO** (implémenté) |
| RBAC conservé | **GO** (tests existants) |
| Vidéo/audio PC ↔ iPhone live | **NO GO** tant que `meet.jit.si` — **GO** après Jitsi dédié + tunnel 8443 |

**Verdict global Phase 2 : GO technique** — **téléconsultation non validée** tant que le test réel PC ↔ iPhone n’a pas réussi avec Jitsi dédié (pas `meet.jit.si`).
