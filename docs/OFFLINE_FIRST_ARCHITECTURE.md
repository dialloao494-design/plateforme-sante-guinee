# Architecture Offline-First — Plateforme Santé Guinée

**Statut :** Proposition d’architecture — **aucune implémentation** avant validation  
**Date :** 2026-07-28  
**Frontend de production de référence (cloud) :** `https://plateforme-sante-guinee.vercel.app`  
**Backend cloud actuel :** FastAPI + PostgreSQL (Railway)  
**Public cible du document :** équipe produit, architecture, sécurité, ops cliniques  

> Ce document **remplace** la vision « PWA / IndexedDB seule » de `OFFLINE_STRATEGY_ROADMAP.md` pour l’objectif métier : **fonctionnement clinique quotidien 100 % sans Internet, durée illimitée**.  
> Internet n’est requis que pour : synchronisation, sauvegarde distante, mises à jour logicielles, administration centralisée.

---

## 1. Principes directeurs

1. **Local-first, cloud-second**  
   La source de vérité opérationnelle d’une clinique est le **nœud local** (serveur clinique). Le cloud est un hub de synchronisation, de sauvegarde et de pilotage multi-cliniques.

2. **Internet jamais sur le chemin critique**  
   Accueil, soins, laboratoire, pharmacie, facturation, impressions PDF, authentification du personnel : **zéro dépendance réseau public**.

3. **Multi-utilisateur en LAN**  
   Plusieurs postes (réception, infirmier, médecin, labo, pharmacie, caisse) travaillent simultanément contre le même serveur local.

4. **Identité et données cloisonnées par clinique**  
   Chaque clinique est un tenant isolé (`clinic_id` + secrets locaux). Pas de fusion accidentelle entre établissements.

5. **Pas de perte de données**  
   Journal d’opérations (append-only), sauvegardes locales automatiques, sync idempotente, conflits explicites — jamais d’écrasement silencieux de faits cliniques.

6. **Continuité avec le produit actuel**  
   Réutiliser le modèle métier existant (patients, admissions, consultations, labo, pharmacie, facturation, rôles) et l’API FastAPI, déployée en **mode clinic-node** plutôt que réécrire un second produit.

---

## 2. Architecture générale

### 2.1 Vue d’ensemble

```
                         ┌──────────────────────────────────────┐
                         │         CLOUD (optionnel)            │
                         │  Hub sync · Backup · Updates · Admin │
                         │  API Railway + Postgres central      │
                         │  Frontend admin (Vercel)             │
                         └──────────────▲───────────────────────┘
                                        │ sync / backup / update
                                        │ (quand Internet dispo)
┌───────────────────────────────────────┴───────────────────────────────────┐
│                     CLINIQUE — RÉSEAU LOCAL (LAN)                         │
│                                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Poste       │  │ Poste       │  │ Poste       │  │ Poste       │     │
│  │ Réception   │  │ Infirmier   │  │ Médecin     │  │ Labo / Phcie│ ... │
│  │ Navigateur  │  │ Navigateur  │  │ Navigateur  │  │ Navigateur  │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │ HTTP/HTTPS LAN  │                │                │            │
│         └─────────────────┴────────┬───────┴────────────────┘            │
│                                    ▼                                      │
│                    ┌───────────────────────────────┐                      │
│                    │   CLINIC NODE (serveur local) │                      │
│                    │  - API FastAPI (mode offline) │                      │
│                    │  - PostgreSQL local           │                      │
│                    │  - Sync agent                 │                      │
│                    │  - Backup agent               │                      │
│                    │  - Update agent               │                      │
│                    │  - SPA servie en local        │                      │
│                    └───────────────────────────────┘                      │
│                                                                           │
│  Option : NAS / 2e disque pour snapshots  ·  Onduleur (UPS) obligatoire  │
└───────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Composants et responsabilités

| Composant | Rôle | Internet requis ? |
|-----------|------|-------------------|
| **Clinic Node** | API + BDD + fichiers + agents | Non (quotidien) |
| **Postes clients** | SPA React dans navigateur, LAN uniquement | Non |
| **Imprimantes** | PDF / tickets via Clinic Node ou impression navigateur | Non |
| **Cloud Hub** | Agrégation multi-cliniques, backup offsite, distribution d’updates | Oui (hors chemin critique) |
| **Console plateforme** | Admin central (déjà existant côté cloud) | Oui |

### 2.3 Modes de déploiement d’un Clinic Node

| Mode | Matériel typique | Usage |
|------|------------------|--------|
| **A — Mini-serveur clinique** | PC / NUC Linux + UPS + disque + SSD | Clinique permanente (recommandé AASMA / Koloma) |
| **B — Appliance Docker** | Même matériel, stack Docker Compose | Installation reproductible |
| **C — Poste unique « serveur + client »** | Un PC fort pour petites structures | Acceptable si ≤ 3 utilisateurs |

**Recommandation produit :** Mode B (Docker Compose) comme unité de déploiement standard.

### 2.4 Découpage logique des services (même machine au départ)

1. `api` — FastAPI (réutilise le code actuel avec feature flags offline)  
2. `db` — PostgreSQL local  
3. `proxy` — Caddy/Nginx (TLS local optionnel, HTTP LAN accepté en phase 1)  
4. `sync-agent` — file d’attente + protocole sync  
5. `backup-agent` — snapshots locaux + upload cloud si online  
6. `update-agent` — télécharge images/versions, bascule atomique  
7. `web` — assets SPA (build Vercel ou build local servi par proxy)

Les agents peuvent démarrer comme **processus/co-routines** dans le même conteneur API en V1, puis être séparés en V2.

### 2.5 Relation avec le cloud actuel

- Le **cloud** conserve le rôle actuel pour cliniques online-only et pour le hub multi-cliniques.  
- Chaque Clinic Node possède un `clinic_id` stable (ex. AASMA = 17) et un `node_id` unique.  
- Le cloud n’est **pas** interrogé pendant les soins.  
- Quand online : le sync-agent pousse/tire des **événements métier** (pas un dump SQL brut comme mécanisme principal).

---

## 3. Base de données locale

### 3.1 Choix : PostgreSQL local (recommandé)

| Critère | PostgreSQL local | SQLite | IndexedDB seule |
|---------|------------------|--------|-----------------|
| Multi-utilisateurs concurrent | Excellent | Limité / fragile | Non (par navigateur) |
| Alignement code actuel (SQLAlchemy) | Direct | Gros écart | Très gros écart |
| Intégrité clinique / transactions | Fort | Moyen | Faible |
| Offline illimité multi-postes | Oui | Difficile | Non |
| Ops backup/PITR | Mature | Possible mais plus pauvre | N/A |

**Décision d’architecture :** PostgreSQL 16+ en local, schéma compatible avec le modèle cloud actuel (même ORM), avec extensions offline (tables sync, outbox, audit).

SQLite / IndexedDB restent éventuellement utiles pour **cache UI** ou mode secours poste isolé, **pas** comme BDD primaire multi-utilisateurs.

### 3.2 Rôle de la BDD locale

- Source de vérité opérationnelle de la clinique  
- Stockage patients, parcours cliniques, facturation, stock pharmacie, catalogues locaux  
- Journal d’audit CIS / actions utilisateurs  
- Tables techniques sync :
  - `sync_outbox` — mutations locales à pousser  
  - `sync_inbox` — mutations cloud/autres nœuds à appliquer  
  - `sync_cursor` — watermarks par stream  
  - `sync_conflicts` — conflits non résolus  
  - `idempotency_keys` — déduplication  
  - `node_metadata` — identité nœud, dernière sync, version logicielle  

### 3.3 Identifiants

Pour éviter les collisions multi-cliniques / multi-nœuds :

| Entité | Stratégie |
|--------|-----------|
| `clinic_id` | Attribué par le cloud à l’installation (entier ou UUID) |
| `node_id` | UUID généré à l’installation du Clinic Node |
| IDs métier locaux (patient, invoice…) | Surrogate local (bigint) **+** `entity_uid` UUID global |
| Numéros affichés (PAT-, INV-, ADM-) | Générés localement avec préfixe clinique (déjà proche du modèle actuel) |

**Règle :** la sync s’effectue sur `entity_uid` / clés métier stables, jamais uniquement sur les `id` auto-incrémentés locaux.

### 3.4 Catalogues et configuration

Répliqués en local (lecture fréquente, écriture rare) :

- Catalogue labo  
- Tarifs / spécialités  
- Stock pharmacie (quantités mutables)  
- Utilisateurs et rôles de la clinique  
- Branding / paramètres d’impression  

Les catalogues « master » peuvent être versionnés (`catalog_version`) pour sync contrôlée depuis le cloud.

---

## 4. Authentification locale et sessions

### 4.1 Principes

- Authentification **100 % locale** (email + mot de passe hashés en BDD locale).  
- JWT (ou session opaque) signé avec un **`NODE_JWT_SECRET` local**, distinct du cloud.  
- Aucun appel Resend / SMTP pour se connecter au quotidien.  
- Reset de mot de passe **local** : procédure admin clinique (réinitialisation par `clinic_admin`) ; reset par email uniquement si Internet + politique activée.

### 4.2 Provisionnement initial des comptes

À l’installation du nœud :

1. Bootstrap d’un compte `clinic_admin` local (mot de passe fort, rotation obligatoire).  
2. Import optionnel des comptes staff existants depuis un **paquet d’installation chiffré** généré par le cloud (one-time).  
3. Ensuite, création/édition des utilisateurs **en local** (même APIs `/clinical/staff` adaptées).

### 4.3 Sessions

| Aspect | Règle |
|--------|-------|
| Durée access token | Courte (ex. 15–60 min) |
| Refresh token | Stocké httpOnly / local sécurisé ; rotation |
| Révocation | Liste de révocation locale + invalidation au changement de mot de passe |
| Multi-postes | Même utilisateur peut ouvrir N sessions ; audit par poste (`device_id`) |
| Verrouillage écran | Timeout d’inactivité côté SPA (exigence clinique) |

### 4.4 Autorisations

Réutiliser le modèle RBAC actuel (`receptionist`, `nurse`, `doctor`, `lab_technician`, `pharmacist`, `cashier`, `clinic_admin`, …) évalué **localement**.  
Aucun rôle cloud (`platform_admin`) n’est requis pour le quotidien clinique.

### 4.5 Horloge et sécurité temps

- NTP LAN / horloge matérielle ; si dérive excessive, alerte admin (la sync et les signatures en dépendent).  
- Les timestamps métier sont stockés en UTC + fuseau clinique affiché.

---

## 5. Réseau local multi-utilisateurs

### 5.1 Topologie

- Switch Ethernet et/ou Wi-Fi clinique dédié (SSID privé).  
- Clinic Node en IP fixe LAN (DHCP reservation).  
- Postes accèdent à `http://sante-locale` ou `http://192.168.x.y` (mDNS / DNS local).  
- **Pas de dépendance DNS public.**

### 5.2 Concurrence

- PostgreSQL gère les transactions concurrentes (ex. deux réceptionnistes).  
- Verrouillage optimiste sur dossiers sensibles (`version` / `updated_at`) pour consultations et stock.  
- File d’attente métier (admission → infirmier → médecin) reste cohérente car une seule BDD.

### 5.3 Impression et fichiers

- Génération PDF **sur le Clinic Node** (ReportLab déjà en place) → téléchargement LAN.  
- Pièces jointes / photos patients stockées sur volume local chiffré (`/data/attachments`).

### 5.4 Isolation réseau recommandée

- Clinic Node **sans exposition Internet entrante** (pas de port-forward).  
- Sortie Internet uniquement sortante (HTTPS) pour sync/backup/update, filtrable par firewall.  
- Option « air-gap volontaire » : admin coupe la sortie ; la clinique continue.

---

## 6. Moteur de synchronisation avec le cloud

### 6.1 Modèle : Event sourcing léger + outbox

Chaque mutation métier locale produit :

1. Écriture transactionnelle dans les tables métier  
2. Insertion atomique dans `sync_outbox` d’un **événement** :

```text
{
  event_id,          // UUID
  clinic_id,
  node_id,
  entity_type,       // patient | admission | invoice | ...
  entity_uid,
  op,                // create | update | delete | status_change
  payload,           // JSON canonique
  schema_version,
  occurred_at,
  actor_user_uid,
  causation_id,      // optionnel
  idempotency_key
}
```

### 6.2 Direction des flux

| Flux | Contenu typique |
|------|-----------------|
| **Push (clinique → cloud)** | Patients, admissions, consultations, résultats labo, prescriptions, dispensations, factures/paiements, audit |
| **Pull (cloud → clinique)** | Mises à jour catalogues, politiques, corrections admin plateforme, (rare) fusion d’identité patient validée |

Pas de sync poste-à-poste entre cliniques. Une clinique = un nœud primaire.

### 6.3 Protocole

- Transport : HTTPS vers Cloud Hub (`/sync/v1/...`)  
- Auth nœud : `node_id` + `node_secret` (mTLS optionnel en V2)  
- Batching : paquets de N événements + curseur  
- Idempotency : le cloud ignore les `event_id` / `idempotency_key` déjà vus  
- ACK : le nœud marque l’outbox `acked` seulement après ACK cloud durable  

### 6.4 Ordre et causalité

- Ordre par `(occurred_at, event_id)` au sein d’une entité.  
- Dépendances explicites si besoin (`requires_entity_uid`).  
- Le cloud applique dans l’ordre ; rejette les événements dont le schéma est inconnu → quarantine + alerte (pas de drop silencieux).

### 6.5 Mode dégradé sync

| État | Comportement |
|------|--------------|
| Offline | Outbox grossit ; UI badge « Sync en attente : N » |
| Online instable | Retry exponentiel + jitter ; circuit breaker |
| Online stable | Drain continu de l’outbox + pull périodique |

**Internet coupé pendant un mois :** aucun impact soins ; sync reprend au retour (voir scénarios).

### 6.6 Ce que l’on ne synchronise pas (par défaut)

- Secrets locaux (`NODE_JWT_SECRET`, clés de chiffrement disque)  
- Backups bruts (canal backup dédié)  
- Logs techniques verbeux (sauf incidents ciblés)

---

## 7. Gestion des conflits

### 7.1 Taxonomie

| Type | Exemple | Stratégie par défaut |
|------|---------|----------------------|
| **Concurrent update** | Deux médecins éditent la même consultation | Version vector / `updated_at` ; **dernier écrit gagne sur champs non critiques** + conservation des deux versions en historique ; champs critiques → conflit manuel |
| **Création dupliquée** | Même patient créé offline sur 2 postes (rare : 1 BDD locale) | Peu probable en LAN mono-nœud ; si import/cloud : rapprochement par téléphone + nom + DOB |
| **Stock pharmacie** | Quantité divergente | **Compteur à deltas** (mouvements), pas écrasement de quantité absolue |
| **Paiement / facture** | Double paiement | Idempotency keys + états de machine (`issued → partial → paid`) |
| **Catalogue** | Tarif cloud vs local modifié | Catalogue cloud versionné ; override local marqué `local_override=true` |

### 7.2 Règles cliniques (non négociables)

- **Ne jamais perdre** une observation clinique saisie (vitaux, diagnostic, résultat labo validé).  
- En conflit de texte clinique : conserver **les deux** dans un historique / `conflict_payload`, signaler à l’admin/médecin.  
- Facturation : préférer la cohérence comptable (pas de montant « magique ») ; écarts → file d’exceptions.

### 7.3 UI conflits

Écran admin clinique :

- Liste des conflits ouverts  
- Diff JSON / champs  
- Actions : « Garder local », « Garder cloud », « Fusionner » (selon type)

### 7.4 Pourquoi les conflits restent rares

Avec **un seul Clinic Node + PostgreSQL**, les conflits intra-clinique sont des courses classiques BDD (gérées par transactions), pas des conflits CRDT complexes.  
Les vrais conflits concernent surtout **clinique ↔ cloud** après longue déconnexion ou corrections plateforme.

---

## 8. Sauvegardes locales et distantes

### 8.1 Sauvegardes locales (obligatoires)

| Type | Fréquence | Contenu | Rétention |
|------|-----------|---------|-----------|
| Snapshot logique `pg_dump` (custom) | Toutes les 1–6 h | BDD complète | 7–14 jours locaux |
| WAL / PITR (si disque le permet) | Continu | Point-in-time | 24–72 h |
| Snapshot volume (LVM/ZFS/Btrfs) | Quotidien | BDD + attachments | 7 jours |
| Copie vers 2e disque / NAS LAN | Quotidien | Derniers snapshots | 30 jours |

**Règle 3-2-1 adaptée clinique :**  
3 copies · 2 supports · 1 offsite (cloud) **quand Internet disponible**.

### 8.2 Sauvegardes distantes (opportunistes)

- Upload chiffré (AES-256-GCM) des snapshots vers le cloud / object storage.  
- Jamais de backup en clair.  
- Metadata : `clinic_id`, `node_id`, `backup_id`, `app_version`, `schema_version`, hash.  
- Si offline prolongé : les backups restent locaux ; reprise d’upload ensuite.

### 8.3 Vérification

- Job hebdomadaire `backup verify` (restore test dans sandbox local).  
- Alerte admin si aucun backup réussi > 24 h.

---

## 9. Chiffrement

### 9.1 Au repos

| Donnée | Mécanisme |
|--------|-----------|
| Volume `/data` | LUKS (disque) ou équivalent OS |
| Backups | Chiffrement applicatif avant écriture/upload (clé clinique) |
| Secrets | Fichier env / Docker secrets, permissions 600 |
| Pièces jointes | Volume chiffré ; noms non significatifs |

**Gestion des clés :**  
- Clé maître clinique dérivée à l’installation (stockée hors BDD, backup papier/coffre admin).  
- Rotation documentée ; jamais embarquée dans les dépôts Git.

### 9.2 En transit

| Lien | Protection |
|------|------------|
| Postes ↔ Clinic Node (LAN) | HTTP accepté en V1 si LAN de confiance ; **HTTPS local** (certificat interne) recommandé dès V1.1 |
| Clinic Node ↔ Cloud | TLS 1.2+ uniquement |
| Sync auth | Bearer node token / mTLS (V2) |

### 9.3 Données sensibles

Alignement CIS / confidentialité patient déjà présent côté audit : conserver et étendre les logs d’accès en local.

---

## 10. Reprise automatique après coupure Internet

### 10.1 Ce qui ne doit PAS s’arrêter

API locale, BDD, sessions, impressions, files d’attente sync (accumulation).

### 10.2 Détection

- Healthcheck sortant périodique vers Cloud Hub (`/sync/v1/ping`).  
- États nœud : `ONLINE` · `DEGRADED` · `OFFLINE`.  
- SPA : bandeau informatif (« Hors ligne Internet — clinique opérationnelle »).

### 10.3 Reprise

1. Détection online  
2. Reprise backup upload (basse priorité)  
3. Drain `sync_outbox` (haute priorité)  
4. Pull catalogues / inbox  
5. Rapport de sync (durée offline, volume d’événements, conflits)

Aucun redémarrage utilisateur requis.

---

## 11. Mises à jour logicielles sans interruption des données

### 11.1 Principes

- **Les données vivent hors du conteneur applicatif** (`volume /data` persistant).  
- Update = remplacer images/binaires, **jamais** reformater le volume data.  
- Migrations Alembic **forward-only**, testées, avec `schema_version` en BDD.

### 11.2 Pipeline update

1. Cloud publie une version (`app_version`, changelog, checksum, migrations min).  
2. `update-agent` télécharge hors heures de pointe (si online).  
3. Pré-checks : espace disque, backup frais obligatoire, compatibilité schéma.  
4. Déploiement **blue/green local** ou restart contrôlé :
   - Arrêt bref API (< 1–2 min cible) **ou** rolling si multi-instance (rare en clinique)  
   - Migration  
   - Healthcheck  
   - Bascule  
5. Rollback image précédent si healthcheck échoue (**data intacte**).

### 11.3 Travail utilisateurs pendant l’update

- Fenêtre de maintenance courte planifiée **ou** update nocturne.  
- Si update forcée : message « Mise à jour — reconnexion dans 2 min » ; les navigateurs se reconnectent ; **aucune perte** grâce aux transactions déjà commit.

### 11.4 Updates offline

- Possibilité d’installer depuis une **clé USB signée** (paquet update) apportée par l’équipe terrain — critique pour cliniques sans Internet fiable.

---

## 12. Déploiement multi-cliniques indépendantes

### 12.1 Modèle

Chaque clinique = **1 Clinic Node** + N postes.  
Aucune dépendance runtime entre cliniques.

### 12.2 Installation type

1. Provision cloud : créer clinique + `clinic_id` + paquet d’activation chiffré  
2. Sur site : installer appliance Docker, importer paquet  
3. Configurer IP LAN, UPS, 2e disque  
4. Créer admin local / importer staff  
5. Premier sync (si Internet) pour catalogues  
6. Recette métier (parcours patient test)  
7. Mise en production locale  

### 12.3 Administration centralisée (cloud)

- Inventaire des nœuds (version, dernière sync, santé backups)  
- Pousser catalogues / politiques  
- Révoquer un nœud volé (`node_secret` rotate + wipe instruction)  
- **Ne pas** piloter les soins en temps réel

### 12.4 Isolation légale / données

- Données d’une clinique A invisibles à la clinique B  
- Exports uniquement via droits admin + audit  

---

## 13. Scalabilité et maintenance

### 13.1 Scalabilité par clinique

| Charge | Approche |
|--------|----------|
| 5–20 utilisateurs concurrent | 1 VM/NUC 4–8 Go RAM, SSD, PostgreSQL local |
| 20–50 utilisateurs | CPU/RAM ↑, pool connexions, éventuel split lecture (rare) |
| Croissance données | Archivage dossiers anciens (toujours consultables), vacuum, monitoring disque |

La scalabilité **inter-cliniques** se fait par **multiplication de nœuds**, pas par un plus gros serveur cloud.

### 13.2 Observabilité locale

- Métriques : CPU, disque, latence API, taille outbox, âge dernière sync, succès backups  
- Logs structurés locaux + export optionnel cloud  
- Tableau de bord admin clinique « Santé du système »

### 13.3 Maintenance

- Patch OS mensuel (fenêtre planifiée)  
- Test restore trimestriel  
- Revue conflits sync  
- Rotation secrets annuelle ou après incident  

---

## 14. Sécurité globale

| Domaine | Mesure |
|---------|--------|
| Accès physique | Serveur dans local fermé ; UPS ; câbles LAN contrôlés |
| Comptes | MFA admin souhaitable dès que faisable offline (TOTP local) |
| RBAC | Rôles minimaux ; séparation caisse / soins |
| Audit | Journal append-only des accès dossiers |
| Malware | OS durci, maj USB signées uniquement |
| Vol de serveur | Volume chiffré ; révocation nœud côté cloud |
| Injection / API | Même discipline FastAPI (validation Pydantic, authz) |
| Impressions | Pas de PHI dans noms de fichiers exposés |

---

## 15. Intégrité des données et anti-perte

### 15.1 Mécanismes

1. **Transactions ACID** PostgreSQL pour chaque acte métier + outbox  
2. **Idempotency keys** sur créations critiques (paiement, patient, résultat labo)  
3. **Append-only audit** (pas de delete hard des audits)  
4. **Soft-delete** patients / documents avec archive  
5. **Checksums** backups + vérification  
6. **Sync ACK** seulement après durabilité cloud  
7. **Interdiction** des jobs « truncate / reset prod » sur Clinic Node  
8. **Gardes migrations** : backup obligatoire avant migrate  

### 15.2 Ce qui est explicitement interdit

- Sync qui écrase une consultation locale plus récente sans conflit visible  
- Suppression de l’outbox non ACK  
- Update applicatif qui monte une image sans volume data monté  
- Réutilisation d’un `node_secret` sur deux machines  

---

## 16. Cartographie fonctionnelle offline (périmètre V1)

| Module | Offline complet | Notes |
|--------|-----------------|-------|
| Authentification staff | Oui | Local |
| Réception (patients, admissions, factures, paiements, remboursements) | Oui | |
| Infirmier (vitaux, évaluations) | Oui | |
| Médecin (consultation, Rx, demandes labo/imagerie) | Oui | |
| Laboratoire (saisie, validation, PDF) | Oui | |
| Pharmacie (stock, dispensation) | Oui | Deltas stock |
| Caisse / recettes du jour | Oui | |
| Impressions PDF | Oui | |
| Hospitalisation / lit | Oui (V1.1 si besoin) | |
| Sync / backup cloud | Opportuniste | |
| Téléconsult / paiements Stripe | Non / dégradé | Hors chemin clinique local |
| Admin plateforme multi-cliniques | Cloud only | |

---

## 17. Scénarios détaillés

### 17.1 Clinique sans Internet pendant un mois

1. Les postes continuent via LAN vers le Clinic Node.  
2. Tous les actes sont persistés en PostgreSQL local.  
3. `sync_outbox` accumule des dizaines/centaines de milliers d’événements (dimensionner disque).  
4. Backups locaux horaires + copie NAS continuent.  
5. Badge UI : « Internet indisponible — N événements en attente ».  
6. Au retour Internet : drain outbox par lots, pull catalogues, rapport de sync, résolution conflits s’il y en a.  
7. **Aucun soin n’a été bloqué** pendant le mois.

**Risques à mitiger :** saturation disque (alertes 80/90 %), dérive horloge, absence de backup offsite pendant la période (compensée par NAS local).

### 17.2 Panne électrique + redémarrage serveur

1. UPS tient le temps du shutdown propre (idéal) ou coupe brutale.  
2. PostgreSQL récupère via WAL (crash recovery).  
3. Docker restart policies (`unless-stopped`) relance api/db/proxy/agents.  
4. Healthcheck local ; SPA se reconnecte.  
5. Sessions JWT : certaines expirées → re-login rapide.  
6. Outbox intacte (disque) → aucune perte des actes commités avant la panne.  
7. Acte en cours non soumis : l’utilisateur resaisit (limite inévitable sans brouillon auto — **brouillons locaux recommandés** sur formulaires longs).

### 17.3 Restauration complète après défaillance disque

1. Constater panne disque primaire.  
2. Remplacer matériel / rattacher 2e disque / NAS.  
3. Réinstaller appliance (même `clinic_id` / `node_id` si restauration identité).  
4. Restore dernier snapshot vérifié + WAL si dispo.  
5. Vérifier `schema_version` / `app_version`.  
6. Démarrer services ; contrôle d’intégrité (comptages patients, dernière facture, stock).  
7. Si Internet : sync catch-up (push des événements non ACK si backup les contenait ; sinon cloud peut renvoyer l’historique ACK pour réconciliation).  
8. Recette métier avant réouverture complète.

**RTO cible :** quelques heures avec NAS local.  
**RPO cible :** ≤ 1 h (fréquence snapshot) ; ≤ minutes avec PITR.

### 17.4 Synchronisation après plusieurs jours hors ligne

1. Passage `OFFLINE` → `ONLINE`.  
2. Auth nœud cloud.  
3. Push outbox par pages (ex. 500 events), pause si erreur réseau.  
4. Cloud déduplique par `event_id`.  
5. Pull inbox (catalogues, corrections).  
6. Ouverture éventuelle de conflits stock/catalogue.  
7. Rapport : durée offline, events poussés, conflicts ouverts, dernière facture sync.  
8. Reprise du rythme de sync normal.

### 17.5 Déploiement d’une nouvelle version sans interrompre (ou presque) le travail

1. Backup automatique déclenché.  
2. Téléchargement image + checksum OK (ou USB signée).  
3. Annonce courte aux utilisateurs (bandeau).  
4. Bascule : arrêt API ~1–2 min, migrate, health OK.  
5. Les navigateurs rechargent la SPA (cache bust).  
6. Données `/data` inchangées.  
7. Si échec : rollback image précédente en < 5 min, data intacte.  
8. Sync-agent reprend avec `schema_version` nouveau.

---

## 18. Plan de livraison architectural (sans code ici)

| Phase | Objectif | Résultat |
|-------|--------|----------|
| **P0 — Fondations nœud** | Appliance Docker + Postgres local + SPA locale + auth locale | Clinique mono-site offline illimitée |
| **P1 — Parité métier** | Tous modules critiques du tableau §16 | Remplace le cloud pour le quotidien |
| **P2 — Sync** | Outbox/inbox + hub cloud + UI conflits | Multi-clinique + continuité cloud |
| **P3 — Backup/update** | Snapshots, offsite chiffré, update agent + USB | Ops production durable |
| **P4 — Durcissement** | HTTPS local, mTLS, TOTP admin, PITR | Niveau hôpital |

Chaque phase se termine par une **recette scénarios §17** avant la suivante.

---

## 19. Décisions ouvertes à valider (avant implémentation)

1. **HTTPS LAN obligatoire dès V1** ou HTTP LAN de confiance accepté temporairement ?  
2. **Matériel de référence** (NUC + UPS + NAS) imposé aux cliniques partenaires ?  
3. **Politique de conflit stock** : strict deltas only — confirmé ?  
4. **Durée max outbox / rétention events** après ACK ?  
5. **Le cloud reste-t-il utilisable en mode online-only** en parallèle des Clinic Nodes (oui recommandé) ?  
6. **Périmètre V1 hospitalisation / imagerie** inclus ou reporté V1.1 ?  

---

## 20. Critères d’acceptation de l’architecture

L’architecture est validée si le comité confirme que :

- [ ] Une clinique peut opérer **sans Internet indéfiniment** pour tous les modules V1  
- [ ] Multi-utilisateurs LAN sur une seule source de vérité locale  
- [ ] Aucune perte d’acte commité après crash électrique (WAL/UPS)  
- [ ] Restore disque avec RPO/RTO acceptables  
- [ ] Sync après longue coupure sans corruption  
- [ ] Update sans destruction du volume data  
- [ ] Isolation stricte multi-cliniques  
- [ ] Chiffrement repos + transit cloud  

**Aucune ligne de code d’implémentation offline-first ne doit démarrer avant validation écrite de ce document** (éventuellement amendé).

---

## 21. Références internes

- Produit cloud actuel : FastAPI + SQLAlchemy + PostgreSQL + React (SPA)  
- Frontend production cloud : `https://plateforme-sante-guinee.vercel.app`  
- Ancien roadmap (périmètre plus étroit, PWA) : `docs/OFFLINE_STRATEGY_ROADMAP.md` — **subordonné** à ce document pour l’objectif « offline illimité »

---

*Fin du document d’architecture — en attente de validation.*
