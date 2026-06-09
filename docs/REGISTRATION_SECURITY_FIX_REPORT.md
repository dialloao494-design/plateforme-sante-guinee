# Rapport de correction — Inscription publique `admin` (audit #1)

**Date :** 2026-05-25  
**Statut :** Corrigé et validé par tests automatisés  
**Périmètre :** uniquement la faille #1 (élévation de privilèges via `POST /auth/register`)

---

## 1. Cause racine

| Couche | Problème initial |
|--------|------------------|
| **API** | `POST /auth/register` acceptait `role: "admin"` et persistait le rôle tel quel. |
| **Schéma** | `UserCreate` autorisait explicitement `patient`, `doctor`, **admin**. |
| **Persistance** | Insertions ORM directes (`pilot_seed`, scripts) sans politique centralisée. |
| **Contournements** | Aucun garde-fou si validation Pydantic contournée ; pas de canal d’approvisionnement admin distinct. |

**Impact clinique :** tout acteur externe pouvait obtenir un compte administrateur (liste utilisateurs, accès transversal, gestion plateforme).

---

## 2. Architecture cible (défense en profondeur)

```
                    ┌─────────────────────────────────────┐
                    │  Client (Signup.jsx)                │
                    │  Rôles UI : patient | doctor seul   │
                    └─────────────────┬───────────────────┘
                                      │ POST /auth/register
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  PublicRegistration (Pydantic)      │
                    │  extra=forbid · assert_public_role  │
                    └─────────────────┬───────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  register_public_user()           │
                    │  channel = public_register          │
                    └─────────────────┬───────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  _persist_user() + policy         │
                    └─────────────────┬───────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  SQLAlchemy before_insert/update    │
                    │  (models/user_hooks.py)           │
                    │  Bloque role=admin sans canal auth  │
                    └─────────────────────────────────────┘

  Admin (hors inscription publique) :
    POST /users/admins  ──► get_current_admin ──► create_admin_user(channel=admin_api)
    ENABLE_ADMIN_BOOTSTRAP ──► bootstrap_initial_admin(channel=admin_bootstrap)
    create_test_user.py + ALLOW_ADMIN_CLI ──► channel=admin_cli
    pytest fixtures ──► channel=test_fixture
```

### Principes

1. **Single entry point** — toute création de compte passe par `services/user_provisioning.py`.
2. **Rôles publics vs privilégiés** — canon dans `core/roles.py` (`PUBLIC_REGISTRATION_ROLES`, `PRIVILEGED_ROLES`).
3. **Canaux d’approvisionnement** — `ContextVar` + hooks ORM (`core/provisioning_context.py`, `models/user_hooks.py`).
4. **Admin uniquement par voies contrôlées** — API admin authentifiée, bootstrap ops, CLI explicite, tests.
5. **Intégrité JWT** — `get_current_user` rejette si `user_role` du token ≠ rôle en base.

---

## 3. Stratégie retenue (et justification)

| Choix | Pourquoi |
|-------|----------|
| Service `user_provisioning` plutôt qu’un simple `if role != admin` dans le routeur | Évite la duplication sur seeds, CLI, futurs endpoints ; testable unitairement. |
| Hooks SQLAlchemy | Bloque les insertions/updates ORM directes (scripts, REPL, bugs futurs). |
| Schéma `PublicRegistration` séparé de `AdminUserCreate` | Séparation claire des contrats API ; mot de passe fort obligatoire pour les admins. |
| `POST /users/admins` | Modèle standard RBAC : seul un admin crée un admin. |
| Bootstrap par variables d’environnement | Premier déploiement sans admin préexistant, sans réouvrir l’inscription publique. |
| Frontend : allowlist côté client **+** serveur | Le client ne fait pas foi ; le serveur reste source de vérité. |

### Risques estimés (avant correction)

| Risque | Probabilité | Impact |
|--------|-------------|--------|
| Prise de contrôle plateforme | Élevée (endpoint public) | Critique |
| Non-conformité / audit sécurité | Certaine | Élevé |

### Risques résiduels (après correction)

| Risque | Mitigation | Note |
|--------|------------|------|
| Premier admin mal configuré (bootstrap) | `ENABLE_ADMIN_BOOTSTRAP` désactivé par défaut ; mot de passe fort requis | Ops |
| `ALLOW_ADMIN_CLI=true` en prod | Documenter interdiction en production | Config |
| Inscription `doctor` sans vérification d’identité | Hors périmètre #1 ; workflow KYC futur | Produit |
| JWT volé (XSS) | Audit #4 (localStorage) | Séparé |

---

## 4. Fichiers modifiés / créés

| Fichier | Rôle |
|---------|------|
| `core/roles.py` | Constantes et validateurs de rôles |
| `core/provisioning_context.py` | Canaux autorisés pour `admin` |
| `models/user_hooks.py` | Garde ORM insert/update |
| `models/__init__.py` | Enregistrement des hooks |
| `services/user_provisioning.py` | Logique métier centralisée |
| `schemas/user.py` | `PublicRegistration`, `AdminUserCreate` |
| `routers/auth.py` | Inscription publique → `register_public_user` |
| `routers/users.py` | `POST /users/admins` |
| `security.py` | `get_current_admin`, cohérence JWT/rôle DB |
| `services/pilot_seed.py` | Seeds via `register_public_user` |
| `services/demo_clinic_seed.py` | Idem |
| `create_test_user.py` | CLI durci + canal `admin_cli` |
| `frontend/.../Signup.jsx` | UI sans option admin |
| `tests/test_registration_security.py` | Suite de régression sécurité |
| `tests/conftest.py` | SQLite StaticPool + désactivation seeds en test |
| `requirements-dev.txt` | `pytest`, `httpx` |

---

## 5. Chemins d’accès couverts

| Chemin | Comportement |
|--------|--------------|
| `POST /auth/register` + `role=admin` | **422** — rejet Pydantic + service |
| Variantes `Admin`, `ADMIN`, typos | **422** |
| Champs extra (`is_admin`, etc.) | **422** — `extra=forbid` |
| Insert ORM direct `User(role=admin)` | **PrivilegedRoleAssignmentError** |
| Update `user.role = admin` | **PrivilegedRoleAssignmentError** |
| JWT forgé `user_role=admin` pour patient | **401** sur endpoints protégés |
| `POST /users/admins` sans token | **401** |
| `POST /users/admins` en tant que patient | **403** |
| Bootstrap sur email existant non-admin | Pas d’escalade |
| Seeds pilot/demo | `register_public_user` uniquement (patient/doctor) |

---

## 6. Tests automatisés

**Commande :**

```bash
python -m pytest tests/test_registration_security.py tests/test_teleconsult_access.py -q
```

**Résultat (2026-05-25) :**

```
29 passed
```

Couverture `test_registration_security.py` :

- Inscription patient / médecin OK
- Rejet admin (casse, typos, champs extra)
- Aucun utilisateur admin créé après attaque
- Provisioning admin (401 / 403 / 201)
- Mot de passe faible admin rejeté
- Garde ORM + escalade bloquée
- JWT forgé rejeté
- Bootstrap désactivé / pas d’escalade
- Canal invalide pour `create_admin_user` rejeté

**Régression téléconsultation :** 9 tests `test_teleconsult_access.py` — OK.

---

## 7. Preuve d’exploitabilité neutralisée

Exécution manuelle (extrait) :

```
POST role=admin     -> 422 Administrator accounts cannot be created via public registration.
POST role=ADMIN     -> 422 (idem)
POST + is_admin     -> 422 Extra inputs are not permitted
POST role=patient   -> 201 role=patient
```

---

## 8. Création du premier administrateur (ops)

**Production recommandée :**

1. Déployer avec `ENABLE_ADMIN_BOOTSTRAP=true` **une seule fois**.
2. Définir `ADMIN_BOOTSTRAP_EMAIL` et `ADMIN_BOOTSTRAP_PASSWORD` (≥ 8 car., majuscule, chiffre).
3. Redémarrer l’API → un admin est créé **si aucun admin n’existe**.
4. Désactiver `ENABLE_ADMIN_BOOTSTRAP` immédiatement après.

**Ensuite :** `POST /users/admins` avec JWT admin pour les comptes suivants.

**Local / CI :** fixture pytest `admin_user` (canal `test_fixture`) ou `ALLOW_ADMIN_CLI=true` + `create_test_user.py`.

---

## 9. Impact sur les autres modules

| Module | Impact |
|--------|--------|
| Auth / login | Aucun changement de contrat ; login inchangé |
| Rendez-vous, paiements, téléconsult | Aucun ; dépendent du rôle JWT aligné DB |
| Frontend Signup | Options limitées patient/doctor ; envoi allowlist |
| Seeds pilot/demo | Utilisent le service public (pas d’admin) |
| `test_teleconsult_access.py` | Pas de régression |
| Documentation legacy (`SECURITY_AUDIT.md`, etc.) | Peut mentionner l’ancien comportement — à mettre à jour hors périmètre |

---

## 10. Checklist production clinique

- [x] Inscription publique ne peut pas créer `admin`
- [x] Voie admin dédiée authentifiée
- [x] Garde ORM anti-contournement
- [x] Tests automatisés dédiés
- [x] JWT ne peut pas usurper un rôle supérieur
- [x] Bootstrap sans escalade de compte existant
- [ ] Aligner politique mot de passe **inscription publique** sur `validate_password` (recommandation future, hors #1)
- [ ] Workflow vérification identité médecin (recommandation produit)

---

*Correction validée — prêt pour revue sécurité #1. Items #2–#7 du plan de remédiation restent ouverts.*
