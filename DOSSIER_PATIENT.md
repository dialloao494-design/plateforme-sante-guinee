# Dossier patient — Plateforme Santé Guinée

**Module :** Patient Dossier MVP (Mission A1)  
**Statut :** Opérationnel en staging/pilote PostgreSQL  
**API :** préfixe `/patients/{patient_id}/...`

---

## 1. Objectif

Centraliser côté serveur les données cliniques d'un patient :

- notes de consultation ;
- synthèses post-consultation ;
- documents médicaux (ordonnances, comptes rendus) ;
- journal d'audit immutable (qui a lu/écrit quoi, quand, depuis quelle IP).

Les données ne sont **plus stockées en localStorage** côté navigateur.

---

## 2. Structure des tables

### 2.1 Vue relationnelle

```
users ──► patients ──┬── clinical_notes ──────► doctors
                     │                    └──► rendezvous (optionnel)
                     ├── consultation_summaries
                     ├── patient_documents
                     └── clinical_audit_logs ◄── (toutes actions dossier)

clinical_audit_logs ──► users (actor_id)
patient_documents ──► users (uploaded_by)
```

### 2.2 Table `patients` (extensions dossier)

Colonnes ajoutées pour le MVP dossier :

| Colonne | Type | Description |
|---------|------|-------------|
| `date_of_birth` | DATE | Date de naissance |
| `phone` | VARCHAR(32) | Téléphone |
| `address` | TEXT | Adresse |
| `emergency_contact` | VARCHAR(255) | Contact d'urgence |
| `created_at` | TIMESTAMP | Création profil |
| `updated_at` | TIMESTAMP | Dernière modification |

### 2.3 Table `clinical_notes`

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `id` | INTEGER | PK | Identifiant |
| `patient_id` | INTEGER | FK → patients | Patient concerné |
| `doctor_id` | INTEGER | FK → doctors | Médecin auteur |
| `appointment_id` | INTEGER | FK → rendezvous | RDV lié (optionnel) |
| `note_type` | VARCHAR(32) | Non | `consultation`, `suivi`, `urgence` |
| `contenu` | TEXT | Non | Corps de la note (1–10 000 car.) |
| `created_at` | TIMESTAMP | Non | Horodatage création |
| `updated_at` | TIMESTAMP | Non | Horodatage modification |

**Index :** `patient_id`, `created_at`

### 2.4 Table `consultation_summaries`

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `id` | INTEGER | PK | Identifiant |
| `patient_id` | INTEGER | FK → patients | Patient |
| `doctor_id` | INTEGER | FK → doctors | Médecin |
| `appointment_id` | INTEGER | FK → rendezvous | RDV lié (optionnel) |
| `diagnostic` | TEXT | Oui | Diagnostic retenu |
| `traitement` | TEXT | Oui | Traitement prescrit |
| `recommandations` | TEXT | Oui | Recommandations de suivi |
| `created_at` | TIMESTAMP | Non | Horodatage |

Au moins un des champs `diagnostic`, `traitement`, `recommandations` doit être renseigné.

### 2.5 Table `patient_documents`

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `id` | INTEGER | PK | Identifiant |
| `patient_id` | INTEGER | FK → patients | Patient |
| `uploaded_by` | INTEGER | FK → users | Utilisateur ayant uploadé |
| `type_document` | VARCHAR(64) | Non | Ex. `prescription`, `lab_result`, `imaging` |
| `file_path` | VARCHAR(255) | Non | Clé opaque stockage (pas de chemin public) |
| `created_at` | TIMESTAMP | Non | Horodatage upload |

**Stockage fichier :** volume Docker `uploads/`, nom opaque généré par `secure_attachment_storage.py`.  
**Accès :** uniquement via `GET /patients/{id}/documents/{doc_id}/download` (authentifié).

Types autorisés : PDF, images (JPEG, PNG), texte. Taille max : 10 Mo.

### 2.6 Table `clinical_audit_logs`

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `id` | INTEGER | PK | Identifiant |
| `actor_id` | INTEGER | FK → users | Utilisateur acteur |
| `actor_role` | VARCHAR(32) | Non | Rôle au moment de l'action |
| `patient_id` | INTEGER | FK → patients | Patient concerné |
| `action` | VARCHAR(32) | Non | `read`, `create`, `update`, `delete` |
| `resource_type` | VARCHAR(64) | Non | Ex. `clinical_note`, `patient_document` |
| `resource_id` | INTEGER | Oui | ID de la ressource |
| `timestamp` | TIMESTAMP | Non | Horodatage UTC |
| `ip` | VARCHAR(64) | Oui | IP client (`X-Forwarded-For` ou direct) |

**Propriété :** table append-only — pas de UPDATE/DELETE applicatif.

---

## 3. API REST

Fichier routeur : `routers/patient_record.py`

| Méthode | Endpoint | Rôles lecture | Rôles écriture |
|---------|----------|---------------|----------------|
| GET | `/patients/{id}/notes` | admin, doctor, patient | — |
| POST | `/patients/{id}/notes` | — | admin, doctor |
| GET | `/patients/{id}/summaries` | admin, doctor, patient | — |
| POST | `/patients/{id}/summaries` | — | admin, doctor |
| GET | `/patients/{id}/documents` | admin, doctor, patient | — |
| POST | `/patients/{id}/documents` | — | admin, doctor (multipart) |
| GET | `/patients/{id}/documents/{doc_id}/download` | admin, doctor, patient | — |
| GET | `/patients/{id}/timeline` | admin, doctor, patient | — |

### 3.1 Exemple — création note

```http
POST /api/patients/1/notes
Authorization: Bearer <token>
Content-Type: application/json

{
  "contenu": "Patient stable, TA 130/85.",
  "note_type": "consultation",
  "appointment_id": 3
}
```

Réponse `201` :

```json
{
  "id": 1,
  "patient_id": 1,
  "doctor_id": 4,
  "appointment_id": 3,
  "note_type": "consultation",
  "contenu": "Patient stable, TA 130/85.",
  "created_at": "2026-06-08T20:46:43",
  "updated_at": "2026-06-08T20:46:43"
}
```

### 3.2 Exemple — création synthèse

```http
POST /api/patients/1/summaries
Authorization: Bearer <token>
Content-Type: application/json

{
  "diagnostic": "HTA grade 1",
  "traitement": "Amlodipine 5 mg/j",
  "recommandations": "Contrôle dans 15 jours",
  "appointment_id": 3
}
```

### 3.3 Exemple — upload document

```http
POST /api/patients/1/documents
Authorization: Bearer <token>
Content-Type: multipart/form-data

type_document=prescription
file=<fichier.pdf>
```

### 3.4 Timeline

`GET /patients/{id}/timeline` agrège chronologiquement :

- notes cliniques ;
- synthèses ;
- documents ;
- rendez-vous associés.

---

## 4. RBAC (contrôle d'accès)

Implémentation : `services/patient_record_access.py`

### 4.1 Lecture dossier (`assert_can_read_dossier`)

| Rôle | Condition d'accès |
|------|-------------------|
| **admin** | Tous les patients |
| **patient** | Uniquement son propre profil (`patients.user_id = current_user.id`) |
| **doctor** | Patient ayant ≥ 1 rendez-vous avec ce médecin |

### 4.2 Écriture clinique (`assert_can_write_clinical`)

| Rôle | Permission |
|------|------------|
| **admin** | Créer notes, synthèses, documents pour tout patient |
| **doctor** | Créer pour patients liés par RDV uniquement |
| **patient** | **Interdit** — HTTP 403 |

### 4.3 Lien médecin ↔ patient

La relation est vérifiée via la table `rendezvous` :

```sql
SELECT 1 FROM rendezvous
WHERE doctor_id = :doctor_id AND patient_id = :patient_id
LIMIT 1;
```

Sans rendez-vous existant, le médecin ne peut ni lire ni écrire le dossier.

### 4.4 Codes HTTP

| Code | Situation |
|------|-----------|
| 200 / 201 | Succès |
| 403 | Rôle insuffisant ou pas de lien RDV |
| 404 | Patient inexistant |
| 422 | Validation Pydantic (contenu vide, type invalide) |

---

## 5. Audit trail

Service : `services/clinical_audit_service.py`

### 5.1 Événements journalisés

| Action | resource_type | Déclencheur |
|--------|---------------|-------------|
| `read` | `clinical_notes` | GET liste notes |
| `read` | `consultation_summaries` | GET liste synthèses |
| `read` | `patient_document` | Download document |
| `create` | `clinical_note` | POST note |
| `create` | `consultation_summary` | POST synthèse |
| `create` | `patient_document` | POST upload |

### 5.2 Champs enregistrés

Chaque entrée capture :

- **Qui** : `actor_id` + `actor_role`
- **Quoi** : `action` + `resource_type` + `resource_id`
- **Sur qui** : `patient_id`
- **Quand** : `timestamp` UTC
- **D'où** : `ip` (header `X-Forwarded-For` via nginx)

### 5.3 Requête d'audit (PostgreSQL)

```sql
SELECT action, resource_type, COUNT(*)
FROM clinical_audit_logs
WHERE patient_id = 1
GROUP BY action, resource_type
ORDER BY 3 DESC;
```

Exemple de résultat pilote :

```
 read   | clinical_notes         | 8
 create | clinical_note          | 2
 create | consultation_summary   | 2
 create | patient_document       | 1
 read   | patient_document       | 1
```

### 5.4 Conformité

- Journal **immutable** (pas d'endpoint DELETE)
- Traçabilité des accès au secret médical
- IP conservée pour investigations incident

> **Limitation actuelle :** pas d'interface admin dédiée pour consulter les logs — requêtes SQL ou export manuel.

---

## 6. Frontend

| Page | Route | Rôle |
|------|-------|------|
| Dossier patient | `/doctor/patient/:id` | doctor, admin |

Composant : `PatientDetails.jsx`

Fonctions :

- affichage notes, synthèses, timeline ;
- création note / synthèse (médecin) ;
- upload document ;
- lien vers rendez-vous et téléconsultation.

API client : `patientRecordAPI` dans `services/api.js`.

---

## 7. Migrations

| Révision Alembic | Fichier | Contenu |
|------------------|---------|---------|
| `20260525_0003_patient_dossier` | `alembic/versions/20260525_0003_patient_dossier.py` | 4 tables cliniques + colonnes patients |
| Fallback SQL | `migrations/20260525_patient_dossier_mvp.sql` | Idempotent PostgreSQL/SQLite |
| Runtime | `database_migrations.ensure_patient_dossier_schema()` | Patch sur DB existantes |

Vérification :

```bash
docker compose exec db psql -U sante -d sante -c "\dt clinical_*"
docker compose exec db psql -U sante -d sante -c "SELECT version_num FROM alembic_version;"
```

---

## 8. Tests de sécurité

Fichier : `tests/test_patient_record_security.py` (16 scénarios)

Couverture :

- patient ne lit que son dossier ;
- médecin sans RDV → 403 ;
- patient ne peut pas créer de note ;
- audit log écrit à chaque read/create ;
- download document authentifié.

---

## 9. Checklist opérationnelle

- [ ] Migration `20260525_0003` appliquée
- [ ] Routes visibles dans `/api/openapi.json`
- [ ] Au moins 1 RDV médecin-patient avant accès dossier
- [ ] Volume `uploads/` monté et persistant
- [ ] Nginx retourne 403 sur `/uploads/` direct
