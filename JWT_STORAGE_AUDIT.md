# Audit sécurité — Blocage #4 : JWT et localStorage

**Date :** 2026-05-25  
**Rôle :** Principal Security Engineer (revue indépendante)  
**Périmètre :** cycle de vie du JWT côté client (React/Vite) et cohérence avec le backend FastAPI  
**Contexte :** corrections #1 (inscription/admin), #2 (paiement), #3 (pièces jointes) considérées livrées ; R1/R2 en cours  
**Méthode :** analyse statique du code, grep exhaustif `localStorage`/`sessionStorage`, revue des mécanismes JWT backend, évaluation des prérequis d'exploitation, recoupement audits V1/V2  
**Statut :** **Problème réel confirmé — criticité réévaluée HIGH (conditionnelle), non CRITICAL**

**Aucune modification de code** n'a été effectuée dans le cadre de cet audit.

---

## 1. Synthèse exécutive

| Question | Réponse |
|----------|---------|
| Le blocage #4 est-il un **problème réel** ? | **Oui** — le JWT d'accès est persisté en `localStorage` et lisible par tout script JS same-origin. |
| Est-ce un **faux positif** ? | **Non** — la surface est avérée dans le code. En revanche, le classer au même niveau que #1–#3 serait **surévaluer** la criticité immédiate. |
| Exploitation **directe sans authentification** ? | **Non** — contrairement à #3 (`/uploads` public) ou #1 (register admin). |
| Prérequis d'exploitation | XSS same-origin, extension navigateur malveillante, accès physique au poste, ou malware lisant le profil navigateur. |
| **Criticité réelle aujourd'hui** | **HIGH / 7,2 sur 10** (impact élevé × probabilité modérée) |
| **Priorité relative post-#1–#3** | **P3** — après R1 (bypass téléconsult) et R2 (IDOR disponibilités), avant ou en parallèle de R3 (dossier serveur) |

**Verdict audit :** le blocage #4 reste un **écart de sécurité architecture SPA authentique et défense en profondeur e-santé**. Ce n'est **pas une faille active exploitable à distance sans condition préalable**, mais c'est le **principal relais** permettant, une fois un token volé, d'accéder à l'intégralité des PHI protégées par l'API (messages, PJ, RDV, profils).

---

## 2. Méthodologie de vérification

1. Inventaire de tous les usages `localStorage` / `sessionStorage` dans `frontend-sante/`.
2. Traçage du flux : login → stockage → `httpClient` → routes protégées → logout / 401.
3. Revue backend : émission JWT, validation, expiration, sync rôle, absence de cookies HttpOnly.
4. Recherche de vecteurs XSS (`dangerouslySetInnerHTML`, `innerHTML`, `eval`, `document.write`).
5. Analyse des en-têtes sécurité (Vercel, nginx) et CSP.
6. Mesure de l'impact des corrections #1–#3 sur la surface d'attaque session.
7. Identification des **faux positifs** et confusions courantes dans la littérature interne du projet.

---

## 3. Constat technique — le JWT est bien en localStorage

### 3.1 Points d'écriture (preuve)

| Fichier | Clés | Moment |
|---------|------|--------|
| `AuthContext.jsx` L132–133 | `token`, `access_token` | Après login réussi |
| `AuthContext.jsx` L72–75 | `user_id`, `user_role` | Après `/auth/me` |
| `AuthContext.jsx` L93–94 | `token` (sync) | Hydratation au chargement |

### 3.2 Points de lecture (preuve)

| Fichier | Usage |
|---------|-------|
| `httpClient.js` L123, L149 | Header `Authorization: Bearer …` sur chaque requête API |
| `ProtectedRoute.jsx` L19 | Garde de navigation client |
| `Sidebar.jsx` L159 | Fallback affichage rôle (secondaire) |

### 3.3 Configuration client HTTP

```117:120:frontend-sante/frontend/src/services/httpClient.js
const httpClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: false,
});
```

**Interprétation :** aucune stratégie cookie HttpOnly n'est implémentée ; le client refuse explicitement l'envoi de cookies cross-origin (`withCredentials: false`).

### 3.4 Backend — émission JWT

```114:114:routers/auth.py
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role})
```

| Paramètre | Valeur | Implication |
|-----------|--------|-------------|
| Algorithme | HS256 | Standard |
| Expiration | `ACCESS_TOKEN_EXPIRE_MINUTES` (défaut **60 min**) | Fenêtre d'abus limitée |
| Refresh token | **Absent** | Pas de rotation ; révocation impossible côté serveur |
| `jti` (ID unique) | **Absent** | Pas de denylist |
| Cookie `Set-Cookie` | **Absent** | Token renvoyé en JSON body uniquement |

**Mitigation backend notable :** `get_current_user` rejette le token si `user_role` ≠ rôle DB — empêche l'**escalade** via JWT forgé ou stale après rétrogradation, **pas** le vol de token valide d'un compte existant.

---

## 4. Le problème est-il toujours réel ?

### 4.1 Oui — arguments factuels

1. **Accessibilité JavaScript :** `localStorage` est synchronement lisible via `localStorage.getItem('token')` depuis n'importe quel script exécuté dans l'origine du SPA.
2. **Persistance cross-session :** le token survit fermeture d'onglet (contrairement à une variable mémoire volatile) jusqu'à expiration JWT ou logout.
3. **Portée du token volé :** avec un JWT patient/médecin/admin valide, l'attaquant accède à **toutes** les ressources API autorisées pour ce rôle — post-#3, cela inclut le téléchargement de PJ cliniques authentifiées, messages, RDV, profils.
4. **Absence de CSP** sur le frontend (Vercel et nginx) — pas de barrière navigateur contre l'injection de script inline ou domaines non autorisés.
5. **Dépendances tierces chargées :** Google Fonts, SDK Jitsi (`@jitsi/react-sdk`) — élargissent la surface supply-chain XSS (probabilité faible mais non nulle).

### 4.2 Scénarios d'exploitation réalistes

| Scénario | Probabilité | Impact |
|----------|-------------|--------|
| XSS stored/reflected dans le SPA | Faible–moyenne (React échappe par défaut ; pas de `dangerouslySetInnerHTML` trouvé) | **Critique** — exfiltration token + appels API en tant que victime |
| Extension Chrome/Firefox malveillante | Moyenne (postes cliniques partagés) | **Élevé** |
| Accès physique poste déverrouillé | Moyenne en clinique | **Élevé** |
| Attaquant réseau distant **sans** XSS | **Nulle** via localStorage seul | — |
| Vol via `Referer` sur token WS | **Non applicable frontend actuel** — le client n'utilise pas encore `/ws/live` | Faible aujourd'hui |

### 4.3 Ce qui n'est **pas** un vecteur direct de #4

- Interception TLS (mitigée par HTTPS prod).
- Fuite du JWT dans les URLs de navigation (token non passé en query sur routes React auditées).
- Accès API **sans** token (fermé par #1–#3 sur les chemins PHI connus).

---

## 5. Faux positifs et sur-interprétations

| Affirmation | Verdict | Commentaire |
|-------------|---------|-------------|
| « JWT localStorage = faille critique immédiate comme `/uploads` public » | **Faux positif de sévérité** | #3 était exploitable sans login ; #4 requiert un prérequis (XSS, etc.) |
| « Le backend JWT est mal implémenté » | **Faux positif** | Bearer + validation + sync rôle est correct ; le gap est **stockage client** |
| « `user_role` en localStorage = blocage #4 » | **Confusion partielle** | Ce n'est pas un bearer token ; risque UX/UI spoofing faible, pas accès API seul |
| « SECURITY_AUDIT_REPORT : acceptable pour SPA » | **Partiellement vrai** | Acceptable MVP générique ; **insuffisant** recommandation OWASP / e-santé PHI |
| « clinicalStorage localStorage = même issue que JWT » | **Confusion fréquente** | Problèmes **liés** (données cliniques côté client) mais **périmètre R3**, pas #4 |
| « sessionStorage serait conforme » | **Faux positif de remédiation** | Même accessibilité JS ; gain marginal (fermeture onglet) |
| « Pas de WebSocket = pas de fuite token » | **Vrai aujourd'hui** | Backend accepte `?token=` sur `/ws/live` — dette future si le frontend branche le live channel |
| « Corrections #1–#3 rendent #4 obsolète » | **Faux** | #4 devient **plus important relativement** car les chemins sans auth sont fermés |

---

## 6. Impact des corrections #1, #2 et #3 sur la criticité de #4

### 6.1 Matrice avant / après

| Capacité attaquant | Avant #1–#3 | Après #1–#3 |
|--------------------|-------------|-------------|
| Devenir admin sans auth | Possible (#1) | **Fermé** |
| Confirmer RDV / téléconsult sans payer (API) | Possible (#2) | **Fermé** (policy) |
| Lire PJ / ordonnances sans login | Possible (#3) | **Fermé** |
| Lire PHI avec JWT volé | Possible | **Toujours possible** |
| Bypass téléconsult (R1, infra) | Possible | **Toujours ouvert** (hors périmètre #4) |

### 6.2 Réévaluation de la criticité

| Dimension | Avant #1–#3 | Après #1–#3 |
|-----------|-------------|-------------|
| **Impact** (si token volé) | Critique | **Critique** — inchangé |
| **Probabilité** d'exploitation du stockage | Moyenne | **Moyenne** — inchangée |
| **Chemins alternatifs sans token** | Nombreux | **Quasi éliminés** |
| **Importance relative de #4** | Noyée parmi failles directes | **Remontée** — devient le principal levier post-auth côté client |
| **Note criticité #4** | 7,0 / 10 | **7,2 / 10** |

**Conclusion :** #4 n'est **pas atténué** par #1–#3 ; il est **mis en évidence** : le JWT volé devient le chemin privilégié d'accès non autorisé aux PHI via l'API.

---

## 7. Mesure de criticité indépendante (2026-05-25)

### 7.1 Score CVSS v3.1 (estimation)

| Métrique | Valeur | Justification |
|--------|--------|---------------|
| Attack Vector | **Network** (via XSS) ou **Local** | Pas d'exploit réseau direct sur localStorage |
| Attack Complexity | **High** | Prérequis XSS ou accès local |
| Privileges Required | **None** (une fois XSS injecté) | — |
| User Interaction | **Required** | Victime doit visiter page piégée |
| Scope | **Unchanged** | Token agit dans le même contexte applicatif |
| Confidentiality | **High** | PHI accessibles via API |
| Integrity | **High** | Actions au nom de la victime (messages, RDV…) |
| Availability | **Low** | Annulations possibles |

**Score estimé : ~7,1 (High)** — comparable à une session hijacking conditionnelle, **inférieur** aux ~9+ des failles #1–#3 historiques.

### 7.2 Classification interne e-santé

| Niveau | Définition | #4 ? |
|--------|------------|------|
| Critique | Exploit distant sans auth, PHI exposée | **Non** |
| Élevé | Exploit conditionnel, impact PHI majeur | **Oui** |
| Moyen | Défaut best practice, impact limité | — |
| Faible | Hygiène | — |

### 7.3 Note de sécurité blocage #4

**7,2 / 10 — ÉLEVÉ, CONDITIONNEL**

- ✅ Problème **réel** et **documenté**
- ⚠️ **Non bloquant** pour un pilote staging fermé si R1/R2 fermés et CSP renforcée
- ❌ **Non conforme** bonnes pratiques OWASP ASVS L2+ / recommandations ANSSI pour applications manipulant des données de santé

---

## 8. Facteurs atténuants (existants)

| Contrôle | Efficacité vs #4 |
|----------|------------------|
| React escaping par défaut | Réduit probabilité XSS |
| `printPrescription.js` utilise `escapeHtml` | Bonne pratique locale |
| Expiration JWT 60 min | Limite fenêtre d'abus |
| Sync rôle JWT ↔ DB | Empêche escalade post-rétrogradation |
| 401 → `clearClientAuth()` | Réduit persistance après invalidation |
| Rate limit login/register | N'empêche pas l'usage d'un token volé |
| HSTS + X-Frame-Options (nginx) | Protège transport / clickjacking, pas XSS |
| PJ sécurisées (#3) | Token requis — **renforce l'enjeu** du vol de token |

---

## 9. Facteurs aggravants (existants)

| Facteur | Détail |
|---------|--------|
| Pas de **Content-Security-Policy** | Aucune policy stricte `script-src` sur SPA |
| Double clé `token` + `access_token` | Redondance, risque de code oubliant l'une des deux au logout |
| `user_id` / `user_role` en clair | Facilite ciblage ; pas équivalent bearer |
| Pas de révocation serveur | Token valide jusqu'à `exp` |
| Données cliniques **aussi** en localStorage (`clinicalStorage.js`) | Exfiltration XSS **sans** appeler l'API — problème **couplé** mais distinct (R3) |
| Backend `/ws/live?token=` | Si frontend adopté plus tard, même token localStorage → fuite logs proxy |
| OWASP : « Ne pas stocker tokens dans localStorage » | Écart documenté |

---

## 10. Comparaison avec les autres travaux en cours

| Item | Type | Criticité | Exploit sans prérequis | Priorité CTO |
|------|------|-----------|------------------------|--------------|
| **R1** Bypass téléconsult | Failles active | Critique | **Oui** | **1** |
| **R2** IDOR disponibilités | Failles active | Élevée | **Oui** (compte médecin) | **2** |
| **#4** JWT localStorage | Faiblesse archi | Élevée conditionnelle | **Non** | **3** |
| **R3** Dossier serveur | Gap produit/conformité | Élevée conformité | Non | **4** |

**Recommandation :** poursuivre R1/R2 en priorité ; planifier #4 en **semaine 2** du plan de remédiation (voir PRODUCTION_READINESS_AUDIT_V2) sans interrompre R1/R2.

---

## 11. Périmètre de remédiation recommandé (sans implémentation)

### 11.1 Cible architecture

```
Option A (recommandée prod) : Cookie HttpOnly + Secure + SameSite=Strict
                              + CSRF token (double-submit ou SameSite Lax + header)
                              + withCredentials: true sur axios

Option B : BFF (Backend-for-Frontend) — session serveur opaque, SPA sans JWT

Option C (palliatif insuffisant seul) : Token en mémoire (variable module)
                                        + refresh via HttpOnly cookie
```

### 11.2 Mesures complémentaires (quick wins)

| Mesure | Effort | Réduction risque |
|--------|--------|------------------|
| CSP stricte (`script-src 'self'`) | 1–2 j | −30 % probabilité XSS |
| Réduire TTL JWT (15–30 min) + refresh HttpOnly | 3–5 j | −40 % fenêtre d'abus |
| Audit dépendances npm (`npm audit`) | 0,5 j | Supply chain |
| Ne pas brancher WS avec token en query | — | Évite amplification |
| Documenter procédure logout forcé admin | 0,5 j | Ops |

### 11.3 Effort correction complète #4

**1 à 2 semaines** (backend cookies + CSRF + refonte AuthContext/httpClient + régression tunnel/LAN/Vercel + tests E2E auth).

---

## 12. Tests et preuves absentes

| Test | Existe ? |
|------|----------|
| Vérification absence token en localStorage post-logout | Manuel seulement |
| Test XSS simulé / CSP | **Non** |
| Test cookie HttpOnly | **Non** (non implémenté) |
| Test vol session cross-origin | **Non** |

**Recommandation QA post-remédiation :** scénario Playwright « injection script → token non lisible » ; test 401 cascade ; test cross-tab logout.

---

## 13. Verdict indépendant

### 13.1 Le blocage #4 est-il un problème réel ?

**OUI.** Le code confirme le stockage persistant du JWT en `localStorage` et son usage systématique pour l'authentification API. C'est un **écart mesurable** par rapport aux recommandations OWASP pour applications traitant des données sensibles.

### 13.2 S'agit-il d'une faille exploitable à distance « ici et maintenant » ?

**NON**, en l'absence de XSS connu ou de compromission du poste. Ce n'est **pas un faux positif de existence**, c'est un **faux positif de criticité immédiate** si classé au niveau des blocages #1–#3.

### 13.3 Criticité réelle après #1, #2, #3

| Attribut | Valeur |
|----------|--------|
| Sévérité | **HIGH (conditionnelle)** |
| Note | **7,2 / 10** |
| Statut blocage #4 | **CONFIRMÉ — NON CORRIGÉ** |
| Bloquant pilote staging fermé ? | **Non** (si R1/R2 OK + pas de XSS) |
| Bloquant production clinique large échelle ? | **Oui** (avec durcissement auth requis) |

### 13.4 Formulation pour comité de direction

> « Le JWT en localStorage n'est pas une porte ouverte comme l'étaient les uploads publics, mais c'est la serrure côté client la plus fragile de la plateforme désormais correctement verrouillée côté serveur. En e-santé, nous devons migrer vers des cookies HttpOnly avant exposition à un grand public. »

---

## 14. Références code auditées

| Fichier | Rôle |
|---------|------|
| `frontend-sante/frontend/src/contexts/AuthContext.jsx` | Login, stockage token |
| `frontend-sante/frontend/src/services/httpClient.js` | Intercepteur Bearer |
| `frontend-sante/frontend/src/routes/ProtectedRoute.jsx` | Garde client |
| `routers/auth.py` | Émission JWT |
| `security.py` | Validation, sync rôle |
| `routers/ws.py` | Token query (dette future) |
| `frontend-sante/frontend/vercel.json` | Headers sans CSP |
| `deploy/nginx/conf.d/app.conf.template` | HSTS, pas CSP SPA |
| `CRITICAL_REMEDIATION_PLAN.md` §4 | Analyse historique cohérente |
| `PRODUCTION_READINESS_AUDIT_V2.md` | R4, priorisation |

---

*Audit indépendant — Blocage #4 JWT/localStorage — Plateforme Santé Guinée. Aucune modification de code.*
