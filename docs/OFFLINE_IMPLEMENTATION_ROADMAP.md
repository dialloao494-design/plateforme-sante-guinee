# Roadmap d’implémentation Offline-First — P0 → Production

**Statut :** Plan d’exécution — **aucune implémentation code** dans ce document  
**Date :** 2026-07-28  
**Référence architecture :** [`OFFLINE_FIRST_ARCHITECTURE.md`](./OFFLINE_FIRST_ARCHITECTURE.md)  
**Frontend cloud actuel :** `https://plateforme-sante-guinee.vercel.app`  
**Backend cloud actuel :** Railway (FastAPI + PostgreSQL)  

> Ce document est le **plan d’exécution** demandé après validation de l’architecture.  
> Ordre : Architecture ✅ → **Roadmap ✅ (ce fichier)** → Validation produit → puis seulement le code.

---

## 0. Règles du plan

1. **Pas de code** tant que ce roadmap n’est pas **validé explicitement**.  
2. Chaque phase a : objectif, livrables, critères de sortie (DoD), dépendances, risques.  
3. Les **contraintes terrain guinéennes** (§1) s’appliquent à **toutes** les phases — elles ne sont pas un add-on final.  
4. Une clinique pilote (Phase 5) précède tout passage production multi-sites.  
5. Le cloud Railway reste opérationnel pour les cliniques non migrées jusqu’au cutover planifié.

---

## 1. Contraintes terrain guinéennes (à anticiper dès P0)

Ces cas sont **fréquents** ou réalistes. L’architecture et chaque phase doivent les traiter explicitement.

| # | Contrainte terrain | Impact | Réponse système / procédure |
|---|-------------------|--------|------------------------------|
| T1 | **Coupures de courant plusieurs fois par jour** | Arrêt brutal possible malgré UPS | UPS obligatoire ; shutdown propre si batterie OK ; PostgreSQL WAL / crash recovery ; services auto-restart ; pas d’écriture critique hors transaction |
| T2 | **UPS / batterie usée** (tient 30 s–2 min seulement) | Peu de temps pour éteindre proprement | Alerte « UPS faible / on battery » (télémétrie + bandeau admin) ; flush agressif ; cible RPO minutes ; test UPS trimestriel dans le runbook |
| T3 | **Extinction brutale du mini-PC** (bouton / débranchement) | Crash OS / BDD | WAL PostgreSQL ; fs journalisé ; `fsck`/remontage auto au boot ; healthcheck post-boot ; jamais de « réparation manuelle SQL » côté technicien |
| T4 | **Câble réseau débranché** / Wi‑Fi clinique down | Postes isolés du serveur | Soins **interrompus sur ce poste** (normal) ; autres postes OK si encore sur LAN ; message UI clair « Serveur injoignable — vérifier câble / Wi‑Fi » ; **aucune** bascule vers le cloud pour les soins |
| T5 | **Poste de travail en panne** | Un rôle sans machine | Autre PC du LAN → même URL HTTPS → login staff ; **zéro donnée métier sur le poste** (navigateur uniquement) |
| T6 | **Remplacement d’urgence du mini-PC** | Serveur HS / vol / panne | Procédure DR &lt; 1 h (archi §21) : NUC secours + `/data` ou restore 2e disque/cloud ; rebind licence ; smoke ; reprise |
| T7 | Internet absent des jours / semaines | Pas de sync / backup distant / update | Clinique 100 % autonome ; outbox locale ; grâce licence multi-mois ; Owner voit « hors ligne » |
| T8 | Technicien non expert Linux | Risque d’erreur ops | Installateur USB UI uniquement ; pas de commandes complexes en procédure standard |
| T9 | Chaleur / poussière / local peu ventilé | Surchauffe, usure SSD | Matériel de référence + checklist entretien ; alertes température/disque si disponibles |
| T10 | Plusieurs utilisateurs concurrentiels sur LAN faible | Latence, timeouts | Timeouts API tolérants ; pas de dépendance temps réel cloud ; tests multi-postes en Phase 2 |

### 1.1 Matrice « continue vs restaure »

| Événement | Les soins continuent ? | Action |
|-----------|------------------------|--------|
| Coupure Internet | **Oui** (LAN) | Aucune |
| Coupure courant + UPS sain | **Oui** quelques minutes puis shutdown propre | Auto |
| Coupure courant + UPS mort + crash | **Reprise après reboot** | Auto-recovery BDD ; vérifier derniers actes commités |
| Câble poste débranché | **Oui sur les autres postes** | Rebrancher / changer de poste |
| Poste HS | **Oui sur un autre poste** | Login ailleurs |
| Mini-PC HS | **Non jusqu’à restore** | Kit DR ; cible &lt; 1 h |
| SSD data HS | **Non jusqu’à restore** | 2e disque / cloud ; cible &lt; 1 h |

---

## 2. Vue d’ensemble des phases

```text
Phase 0  Foundation appliance (serveur, Postgres, Docker, install USB)
    │
Phase 1  Auth locale · sessions · permissions
    │
Phase 2  API locale · frontend LAN · multi-utilisateurs
    │
Phase 3  Sauvegardes · sync deltas · conflits · licences (jeton local)
    │
Phase 4  Mises à jour · Owner dashboard · monitoring / alertes
    │
Phase 5  Clinique pilote · migration Cloud→Node · validation · production
```

| Phase | Nom court | Sortie attendue |
|-------|-----------|-----------------|
| **0** | Foundation | Appliance installable &lt; 30 min, Postgres up, HTTPS local, reboot-safe |
| **1** | Identité locale | Staff se connecte **sans Internet** avec RBAC |
| **2** | Soins sur LAN | Parcours cliniques V1 sur serveur local, multi-postes |
| **3** | Résilience data | Backups + sync + conflits + licence offline |
| **4** | Ops distantes | Updates + Owner + alertes (sans PHI) |
| **5** | Pilote → Prod | Une clinique réelle validée, puis go-live contrôlé |

---

## 3. Phase 0 — Foundation (serveur local, PostgreSQL, Docker, install)

### 3.1 Objectif

Préparer le **Clinic Node** installable : matériel de référence, runtime, base, scripts/installateur, comportement face aux coupures (T1–T3).

### 3.2 Travaux (plan — pas encore de code)

| # | Travail | Détail |
|---|---------|--------|
| 0.1 | Décider le packaging runtime | **Docker Compose** retenu par défaut (isolé, reproductible) ; alternative documentée si contrainte terrain |
| 0.2 | Image / clé USB d’installation | Boot → assistant UI « Installer » ; aucune commande complexe |
| 0.3 | Volume `/data` | Persistant, chiffré (LUKS), hors image applicative |
| 0.4 | PostgreSQL local | Création auto, migrations, utilisateurs BDD internes |
| 0.5 | Proxy HTTPS | Certificat local auto (CA nœud) |
| 0.6 | Services | API + web + agents (stubs OK en P0) auto-start au boot |
| 0.7 | Auto-recovery | Restart policies ; smoke post-boot après crash simulé |
| 0.8 | Checklist UPS | Doc : brancher UPS, test coupure 10 s, alerte batterie |

### 3.9 Livrables

- Spéc installateur USB + contrats d’interfaces (`/data`, ports, health)  
- Runbook technicien 1 page (brouillon)  
- Matrice tests crash : kill -9 Postgres, hard power-off, reboot  

### 3.10 Critères de sortie (DoD)

- [ ] Install neuve &lt; 30 min sur NUC de référence (chrono chronométré)  
- [ ] Après extinction brutale : reboot → services UP → BDD cohérente  
- [ ] Accès `https://…` local (certificat auto)  
- [ ] Aucune commande manuelle dans le parcours technicien standard  

### 3.11 Risques

| Risque | Mitigation |
|--------|------------|
| Docker trop lourd sur petit NUC | Benchmark RAM ; limites compose ; fallback services système si besoin |
| Certificat rejeté par navigateurs | Script « confiance CA » 1 clic + doc |

---

## 4. Phase 1 — Authentification, sessions, permissions locales

### 4.1 Objectif

Le Clinic Node authentifie le personnel **100 % localement** (T7 : sans Internet).

### 4.2 Travaux

| # | Travail |
|---|---------|
| 1.1 | Store credentials local (hash) + seed admin à l’install |
| 1.2 | JWT / sessions signés avec secret nœud |
| 1.3 | RBAC : réception, médecin, infirmier, labo, pharmacie, caisse, admin clinique |
| 1.4 | Timeout inactivité SPA |
| 1.5 | Reset MDP admin local (sans email obligatoire) |
| 1.6 | Horloge / dérive : alerte si clock skew (licences + audit) |

### 4.3 Critères de sortie

- [ ] Login / logout multi-rôles **offline**  
- [ ] Refus d’accès hors permission  
- [ ] Session survit au redémarrage API (refresh policy documentée)  
- [ ] Extinction brutale pendant login : pas de corruption comptes |

---

## 5. Phase 2 — API locale, frontend LAN, multi-utilisateurs

### 5.1 Objectif

Reproduire les parcours V1 (accueil → caisse) contre l’API **locale** ; plusieurs postes simultanés (T4, T5, T10).

### 5.2 Travaux

| # | Travail |
|---|---------|
| 2.1 | Mode `clinic-node` de l’API (même codebase FastAPI, config locale) |
| 2.2 | SPA servie localement ; config API = hôte LAN HTTPS |
| 2.3 | Parité fonctionnelle modules V1 (hors hospit/imagerie = V1.1) |
| 2.4 | Transactions + journal / outbox **stubs** (événements écrits même si sync pas encore live) |
| 2.5 | Autosave brouillons formulaires longs |
| 2.6 | Tests multi-postes : 6 rôles en parallèle sur LAN |
| 2.7 | UI états réseau : serveur injoignable (câble) vs Internet absent |

### 5.3 Critères de sortie

- [ ] Parcours complets sans Internet  
- [ ] 2+ postes concurrentiels sans corruption  
- [ ] Remplacement d’un poste HS : reprise immédiate sur autre PC  
- [ ] Débranchement câble : message clair ; autres postes non impactés  

---

## 6. Phase 3 — Sauvegardes, synchronisation, conflits, licences

### 6.1 Objectif

Résilience des données (T1–T3, T6, T7) + lien cloud opportuniste + licence clinique.

### 6.2 Travaux

| # | Travail |
|---|---------|
| 3.1 | Backup local automatique (défaut 30 min) + rétention + 2e disque si présent |
| 3.2 | Restore one-click / assistant (prérequis DR) |
| 3.3 | Sync engine : outbox/inbox **deltas** ; stock = mouvements historisés |
| 3.4 | Idempotence + ACK cloud |
| 3.5 | UI conflits admin (pas d’écrasement silencieux) |
| 3.6 | Upload backup distant chiffré (si Internet) |
| 3.7 | Licence : jeton local, grâce 90–180 j, renouvellement transparent |
| 3.8 | Heartbeat ops minimal (prépare Phase 4) |

### 6.3 Critères de sortie

- [ ] Restore depuis backup local chronométré &lt; 1 h (scénario NUC de secours)  
- [ ] Sync après 7 jours offline simulés sans perte d’événements  
- [ ] Conflit stock / texte : file visible admin  
- [ ] Licence en grâce : soins possibles + alerte admin  

---

## 7. Phase 4 — Mises à jour, tableau Owner, monitoring

### 7.1 Objectif

Ops siège (France / ailleurs) sans accès PHI ; updates sûrs sur terrain instable.

### 7.2 Travaux

| # | Travail |
|---|---------|
| 4.1 | Update agent : paquet signé (réseau ou USB) ; backup avant migrate ; rollback |
| 4.2 | Owner dashboard : online/offline, version, sync, backups, disque, licence, outbox |
| 4.3 | Alertes : silence heartbeat, sync en panne, backup manquant, disque faible, UPS |
| 4.4 | Canal télémétrie **strictement ops** (liste blanche champs — archi §23) |
| 4.5 | Runbooks support : câble, poste HS, NUC HS, UPS usée |

### 7.3 Critères de sortie

- [ ] Owner voit une clinique « offline » sans aucun champ patient  
- [ ] Alerte déclenchée si sync &gt; 48 h (lab)  
- [ ] Update + rollback testés sur NUC  
- [ ] Mise à jour USB sans Internet réussie |

---

## 8. Phase 5 — Pilote clinique, validation, production

### 8.1 Objectif

Une **clinique pilote réelle** ; migration Cloud → Node si données Railway existantes ; go-live production contrôlé.

### 8.2 Travaux

| # | Travail |
|---|---------|
| 5.1 | Sélection clinique pilote + formation staff (1 journée) |
| 5.2 | Déploiement terrain : mini-PC + UPS + USB (&lt; 30 min) |
| 5.3 | Si données cloud : **migration Railway → Node** (archi §25) — freeze, export, import, checksums |
| 5.4 | Semaine d’hypercare : coupsures réelles, sync, backups, Owner |
| 5.5 | Exercice DR réel : swap NUC ou restore 2e disque |
| 5.6 | Revue validation (checklist §9) |
| 5.7 | Décision go / no-go production |
| 5.8 | Industrialisation : kit standard, stock NUC secours, process licences |

### 8.3 Critères de sortie pilote

- [ ] ≥ 5 jours ouvrés de soins **sans** dépendance Internet  
- [ ] Au moins une coupure courant réelle traversée sans perte d’actes commités  
- [ ] Backup local + distant (si Internet) OK  
- [ ] Owner dashboard utilisé par le siège  
- [ ] Exercice remplacement NUC &lt; 1 h  
- [ ] Feedback staff intégré (P1 bugs bloquants = 0) |

### 8.4 Passage production

1. Gel des critères go-live signés (produit + ops + clinique).  
2. Migration clinique par clinique (jamais big-bang national).  
3. Cloud = hub secondaire pour cliniques migrées.  
4. Support N1 terrain / N2 siège avec runbooks T1–T10.

---

## 9. Checklist de validation globale (avant « production »)

### 9.1 Fonctionnel

- [ ] Auth locale multi-rôles  
- [ ] Parcours V1 complets offline  
- [ ] Impressions PDF locales  
- [ ] Stock historisé + deltas  

### 9.2 Résilience terrain

- [ ] Coupures courant répétées (lab + pilote)  
- [ ] UPS usée simulée (shutdown court)  
- [ ] Hard power-off mini-PC  
- [ ] Câble débranché  
- [ ] Poste HS → autre poste  
- [ ] Remplacement NUC d’urgence  

### 9.3 Ops / cloud secondaire

- [ ] Sync opportuniste + conflits  
- [ ] Backups locaux + restore  
- [ ] Licence grâce + renouvellement  
- [ ] Owner sans PHI  
- [ ] Updates signées (+ USB)  

### 9.4 Migration

- [ ] Runbook Cloud → Node exécuté une fois avec succès sur pilote (si applicable)  

---

## 10. Ordre des tickets (découpage conseillé après validation roadmap)

> À transformer en tickets GitHub **seulement après validation** de ce document.

| ID | Phase | Ticket (titre indicatif) |
|----|-------|--------------------------|
| T-000 | 0 | Spec appliance + contrat `/data` + health endpoints |
| T-001 | 0 | Installateur USB UI (parcours sans CLI) |
| T-002 | 0 | Postgres auto + migrations + volume chiffré |
| T-003 | 0 | HTTPS local + CA trust script postes |
| T-004 | 0 | Suite tests crash/reboot (CI ou banc NUC) |
| T-010 | 1 | Auth locale + RBAC + sessions |
| T-020 | 2 | Mode clinic-node API + SPA LAN |
| T-021 | 2 | Parité modules V1 + autosave |
| T-022 | 2 | Campagne test multi-postes |
| T-030 | 3 | Backup/restore local |
| T-031 | 3 | Sync deltas + stock movements |
| T-032 | 3 | Conflits UI + idempotence |
| T-033 | 3 | Licences (jeton + grâce) |
| T-040 | 4 | Update agent + rollback |
| T-041 | 4 | Heartbeat ops + Owner dashboard + alertes |
| T-050 | 5 | Outil migration Railway → Node |
| T-051 | 5 | Pilote terrain + exercice DR |
| T-052 | 5 | Go-live production checklist |

Hospit / imagerie : **hors** ce chemin critique → backlog **V1.1** (schéma déjà prévu dans l’architecture).

---

## 11. Hors scope de ce roadmap (rappel)

- Implémentation code (interdit tant que non ordonné)  
- Refonte UX cloud pure  
- Modules hospitalisation / imagerie (V1.1)  
- Sync clinique ↔ clinique directe  

---

## 12. Décision demandée au valideur

Merci de valider explicitement :

1. **Ce roadmap d’exécution** (phases 0 → 5)  
2. La prise en compte des **contraintes terrain T1–T10**  
3. Le packaging **Docker Compose** comme défaut Phase 0 (ou alternative souhaitée)  
4. La clinique **pilote** pressentie (nom / `clinic_id`) — peut rester « à désigner »  

Une fois validé : **Architecture ✅ · Roadmap ✅ · Validation ✅** → ouverture des tickets Phase 0 et **seulement alors** le code.

---

*Document de planification — 2026-07-28 — lié à `OFFLINE_FIRST_ARCHITECTURE.md`.*
