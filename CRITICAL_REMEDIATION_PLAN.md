# Plan de remédiation critique — validation technique

**Date :** 2026-05-25  
**Référence :** `ENGINEERING_AUDIT_REPORT.md` — section **10.A Top 20**, items **#1 à #7**  
**Méthode :** relecture du code source uniquement (aucune modification appliquée)  
**Objectif :** confirmer ou infirmer chaque blocage, fournir la preuve exacte, réévaluer la criticité et proposer la correction minimale.

---

## Synthèse

| # | Blocage (audit) | Problème réel ? | Criticité réévaluée | Délai estimé |
|---|-----------------|-----------------|---------------------|--------------|
| 1 | Inscription `admin` ouverte | **Oui** | **Critique** | < 30 min |
| 2 | `confirm-payment` sans Stripe | **Oui** | **Critique** | < 2 h |
| 3 | `/uploads` sans JWT | **Oui** | **Critique** | < 1 jour |
| 4 | JWT en `localStorage` | **Oui** (risque conditionnel XSS) | **Haute** | > 1 jour |
| 5 | Synthèses cliniques non persistées | **Oui** | **Haute** | < 1 jour |
| 6 | `PUT /appointments` sans garde paiement | **Oui** | **Haute** | < 2 h |
| 7 | IDOR créneaux médecin | **Oui** | **Haute** | < 2 h |

**Verdict global :** les 7 conclusions de l’audit sont **fondées**. Aucun faux positif sur le périmètre analysé. La criticité du #4 et du #5 est légèrement **abaissée** par rapport au libellé « Critique » de l’audit pour #4 (exploitation indirecte) ; le #6 reste **Haute** (pas Critique) car il exige un compte médecin/admin authentifié, mais le contournement paiement est **démontrable en production** via le frontend actuel.

---

## 1. Inscription publique avec rôle `admin`

### 1.1 Validation

| Champ | Valeur |
|-------|--------|
| **Problème réel ?** | **Oui** — tout client HTTP peut envoyer `role: "admin"` à l’inscription. |
| **Criticité réelle** | **Critique** — élévation de privilèges à la création de compte, sans contrôle serveur supplémentaire. |

### 1.2 Preuve dans le code

Le schéma Pydantic **accepte explicitement** `admin` :

```26:32:schemas/user.py
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        role = v.strip().lower()
        if role not in {"patient", "doctor", "admin"}:
            raise ValueError("Role must be one of: patient, doctor, admin")
        return role
```

Le routeur **persiste** le rôle tel quel, sans filtrage métier :

```48:54:routers/auth.py
    hashed_pw = hash_password(user.password)
    new_user = User(
        email=user.email.lower().strip(),
        hashed_password=hashed_pw,
        role=user.role,
    )
```

La doc OpenAPI du endpoint confirme l’intention exposée :

```32:34:routers/auth.py
    - role: One of 'patient', 'doctor', 'admin' (defaults to 'patient')
```

### 1.3 Correction minimale

- Dans `schemas/user.py` : n’autoriser que `patient` et `doctor` à l’inscription publique **ou** ignorer `role` côté API et forcer `patient` par défaut.
- Création `admin` : endpoint séparé réservé à un `admin` existant (ou script ops / seed).

### 1.4 Estimation

**< 30 min** (validator + test API + doc).

---

## 2. `POST /payments/{id}/confirm-payment` sans preuve Stripe

### 2.1 Validation

| Champ | Valeur |
|-------|--------|
| **Problème réel ?** | **Oui** — un patient authentifié peut marquer un RDV `paid` + `confirmed` sans aucun appel Stripe ni webhook. |
| **Criticité réelle** | **Critique** — fraude paiement / téléconsultation sans encaissement. |

### 2.2 Preuve dans le code

Endpoint : aucune importation ni vérification `StripeService`, signature, `session_id`, ni état webhook :

```153:214:routers/payments.py
@router.post("/{rdv_id}/confirm-payment", response_model=rendezvous_schemas.RendezVousResponse)
def confirm_payment_simple(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_patient),
):
    ...
    appointment.payment_status = "paid"
    appointment.status = "confirmed"
    appointment.updated_at = datetime.utcnow()
    db.commit()
```

Le frontend **appelle ce chemin** après « paiement » :

```88:88:frontend-sante/frontend/src/services/api.js
  confirmPayment: (appointmentId) => httpClient.post(`/payments/${appointmentId}/confirm-payment`),
```

```281:283:frontend-sante/frontend/src/pages/Appointments.jsx
      // Call backend to mark appointment as paid
      const response = await paymentsAPI.confirmPayment(appointment.id);
```

**Note :** un webhook Stripe existe (`routers/payments.py` L232+), mais il constitue un **canal parallèle** ; il ne protège pas `confirm-payment`. Un second endpoint `/rendezvous/{id}/confirm-payment` existe aussi sans preuve Stripe (`routers/rendezvous.py` L182-194) — le frontend principal utilise `/payments/...`.

Scripts E2E reposent sur ce comportement (mode test), ce qui confirme l’usage intentionnel en dev, pas une absence de route.

### 2.3 Correction minimale

- **Production :** supprimer ou retourner `403` sur `confirm-payment` sauf si `ENVIRONMENT=development` **et** flag explicite `ALLOW_STUB_PAYMENT=true`.
- **Flux nominal :** confirmer uniquement via `StripeService` + webhook (ou `GET session` Stripe côté serveur avec `session_id` fourni par le client après redirect).
- Aligner le frontend : ne plus appeler `confirmPayment` en prod ; attendre le webhook ou un endpoint `GET /payments/{id}/status` basé sur Stripe.

### 2.4 Estimation

**< 2 h** (garde-fou env + branchement webhook / statut session ; tests manuels Stripe).

---

## 3. Fichiers `/uploads` servis sans authentification

### 3.1 Validation

| Champ | Valeur |
|-------|--------|
| **Problème réel ?** | **Oui** — montage statique public au niveau application. |
| **Criticité réelle** | **Critique** — pièces jointes messagerie (potentiellement médicales) accessibles par URL devinable ou fuitée. |

### 3.2 Preuve dans le code

Montage sans middleware d’auth :

```109:111:main.py
uploads_dir = Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
```

Écriture disque + URL publique prévisible :

```101:113:routers/messages.py
        appointment_folder = UPLOAD_ROOT / f"appointment_{appointment_id}"
        ...
        attachment_url = f"/uploads/messages/appointment_{appointment_id}/{unique_name}"
```

`unique_name` inclut un horodatage (`%Y%m%d%H%M%S%f`) — **obscurité faible**, pas contrôle d’accès : toute requête `GET /uploads/...` sans JWT aboutit au fichier si l’URL est connue.

### 3.3 Correction minimale

- Retirer `StaticFiles` public ; servir via route `GET /messages/attachments/{id}` avec `get_current_user` + vérification participation au RDV.
- Alternative rapide intermédiaire : signed URLs (token HMAC court TTL) générées à l’upload.

### 3.4 Estimation

**< 1 jour** (route protégée + migration URLs existantes en base ; tests messagerie).

---

## 4. JWT stocké en `localStorage`

### 4.1 Validation

| Champ | Valeur |
|-------|--------|
| **Problème réel ?** | **Oui** — token lisible par tout script JS de la page (XSS). |
| **Criticité réelle** | **Haute** (pas Critique immédiate) — exploitation **conditionnelle** à une faille XSS ou extension malveillante ; impact maximal sur PHI si XSS présent. |

### 4.2 Preuve dans le code

Stockage au login :

```131:133:frontend-sante/frontend/src/contexts/AuthContext.jsx
      localStorage.setItem('token', access_token);
      localStorage.setItem('access_token', access_token);
```

Lecture sur chaque requête API :

```123:123:frontend-sante/frontend/src/services/httpClient.js
  const token = localStorage.getItem('token') || localStorage.getItem('access_token');
```

Route protégée côté client :

```19:19:frontend-sante/frontend/src/routes/ProtectedRoute.jsx
  const token = localStorage.getItem('token') || localStorage.getItem('access_token');
```

Données cliniques **également** en `localStorage` (`clinicalStorage.js`, voir #5) — surface d’exfiltration élargie.

### 4.3 Correction minimale

- Court terme : durcir CSP, audit XSS, rotation courte JWT, `httpOnly` + `Secure` + `SameSite` cookies via refactor login backend.
- Ne pas traiter seul le déplacement du token sans revue XSS globale.

### 4.4 Estimation

**> 1 jour** (cookies session + CORS/credentials + régression auth mobile/tunnel).

---

## 5. Synthèses cliniques non persistées côté serveur

### 5.1 Validation

| Champ | Valeur |
|-------|--------|
| **Problème réel ?** | **Oui** — aucune table/API pour les synthèses de consultation ; uniquement navigateur. |
| **Criticité réelle** | **Haute** — perte de données, non-conformité gouvernance clinique ; pas une faille d’intrusion directe comme #1–#3. |

### 5.2 Preuve dans le code

Module entièrement `localStorage` :

```1:32:frontend-sante/frontend/src/utils/clinicalStorage.js
const STORAGE_KEY = 'psg_clinical_summaries_v1';
...
export function setConsultationSummary(appointmentId, patientId, text) {
  ...
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}
```

Utilisation en salle de consultation :

```581:581:frontend-sante/frontend/src/pages/ConsultationRoom.jsx
      setConsultationSummary(appointment.id, appointment.patient_id, summaryDraft.trim());
```

Lecture dossier patient :

```8:8:frontend-sante/frontend/src/pages/PatientDetails.jsx
import { getConsultationSummary } from '../utils/clinicalStorage.js';
```

Recherche backend : **aucun** router/model dédié `consultation_summary` / `clinical_notes` dans `routers/` ou `models/`.

Notes libres patient (`PatientDetails.jsx` L63-75) : également `localStorage` par clé ad hoc — même classe de problème.

### 5.3 Correction minimale

- Table `consultation_notes` (`appointment_id`, `author_user_id`, `body`, `created_at`).
- `POST/GET /appointments/{id}/clinical-summary` avec contrôle rôle (médecin du RDV, patient concerné, admin).
- Migration one-shot optionnelle depuis export manuel (hors scope minimal).

### 5.4 Estimation

**< 1 jour** (modèle + routes + branchement `ConsultationRoom` / `PatientDetails`).

---

## 6. `PUT /appointments/{id}` confirme sans garde paiement

### 6.1 Validation

| Champ | Valeur |
|-------|--------|
| **Problème réel ?** | **Oui** — divergence confirmée avec `/rendezvous` qui impose `payment_status == 'paid'`. |
| **Criticité réelle** | **Haute** — contournement métier exploité par le **frontend médecin** actuel ; nécessite compte authentifié. |

### 6.2 Preuve dans le code

**Garde présente** sur `/rendezvous` :

```145:150:routers/rendezvous.py
    if update.status == "confirmed" and appointment.payment_status != "paid":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot confirm appointment without payment. Patient must pay first."
        )
```

**Absente** sur `/appointments` :

```130:158:routers/appointments.py
@router.put("/{appointment_id}", response_model=rendezvous_schemas.RendezVousResponse)
def update_appointment(
    ...
    return RendezVousService.update_appointment_status(
        rdv_id=appointment_id,
        new_status=update.status,
        db=db,
    )
```

Le service autorise la transition `pending` → `confirmed` **sans** vérifier `payment_status` :

```59:62:services/rendezvous_service.py
    VALID_TRANSITIONS = {
        "pending": ["paid", "confirmed", "cancelled"],
```

```444:451:services/rendezvous_service.py
        allowed_next_states = RendezVousService.VALID_TRANSITIONS[rdv.status]
        if new_status not in allowed_next_states:
            raise HTTPException(...)
```

**Chaîne d’exploitation UI :**

```76:76:frontend-sante/frontend/src/services/api.js
  updateStatus: (id, status) => httpClient.put(`/appointments/${id}/`, { status }),
```

```92:92:frontend-sante/frontend/src/pages/DoctorAppointments.jsx
      await appointmentsAPI.updateStatus(appointmentId, 'confirmed');
```

Scénario : RDV `pending` / `payment_status != paid` → médecin clique confirmer → `confirmed` sans paiement (tant que #2 n’a pas été abusé par le patient).

### 6.3 Correction minimale

- Copier le bloc « PAYMENT GATE » de `rendezvous.py` dans `appointments.py` **ou** centraliser dans `RendezVousService.update_appointment_status` (une seule source de vérité).
- À terme : déprécier l’un des deux préfixes API.

### 6.4 Estimation

**< 2 h** (garde + test d’intégration ; vérifier flux médecin).

---

## 7. IDOR sur les créneaux de disponibilité médecin

### 7.1 Validation

| Champ | Valeur |
|-------|--------|
| **Problème réel ?** | **Oui** — un médecin authentifié peut modifier le planning d’un **autre** `doctor_id`. |
| **Criticité réelle** | **Haute** — sabotage planning / disponibilités ; pas d’accès anonyme. |

### 7.2 Preuve dans le code

Endpoints `POST/PUT/DELETE` sur `/{doctor_id}/availability` : rôle `doctor` ou `admin`, **sans** lier `doctor_id` au profil du user courant.

Exemple création :

```188:193:routers/doctor.py
@router.post("/{doctor_id}/availability", response_model=DoctorAvailabilityResponse)
def create_doctor_availability(
    doctor_id: int,
    ...
    current_user=Depends(require_roles(["admin", "doctor"])),
):
```

Aucune occurrence de `Doctor.user_id == current_user.id` dans ces handlers (contrairement à `get_my_doctor_profile` L106).

Mise à jour — même schéma :

```252:258:routers/doctor.py
@router.put("/{doctor_id}/availability/{availability_id}", ...
    current_user=Depends(require_roles(["admin", "doctor"])),
):
```

**Contre-preuve partielle :** l’audit ne surestime pas — ce n’est pas un IDOR sur les RDV patients, mais bien sur le **calendrier médecin**.

### 7.3 Correction minimale

- Helper `_assert_doctor_scope(db, current_user, doctor_id)` : si `role == doctor`, exiger `doctor.user_id == current_user.id` ; `admin` exempté.
- Appliquer sur POST/PUT/DELETE availability.

### 7.4 Estimation

**< 2 h** (helper + 3 handlers + test IDOR).

---

## Ordre de remédiation recommandé

1. **#1** Inscription admin — blocage immédiat avant tout déploiement.
2. **#2** Paiement fictif — impact financier direct.
3. **#6** Garde paiement sur `PUT /appointments` — alignement avec flux médecin réel.
4. **#3** Fichiers uploads — exposition PHI.
5. **#7** IDOR planning — intégrité opérationnelle clinique.
6. **#5** Persistance synthèses — continuité des soins / conformité.
7. **#4** Session httpOnly — durcissement long terme (en parallèle CSP / XSS).

---

## Écarts audit vs validation

| Point audit | Commentaire validation |
|-------------|------------------------|
| Synthèse exécutive cite aussi « schéma DB triple mécanisme » | **Réel** (`main.py` `create_all`, `database_migrations`, `RendezVousService.ensure_schema`) mais **hors Top 7** — item #11–#12 du plan audit ; risque **Moyen** (dérive schéma), pas bloquant go-live immédiat comme #1–#3. |
| `JOINABLE_STATUSES` + `pending` | **Réel** (`teleconsultation_access.py` L58) — item **#9** audit, **Moyen** ; non inclus dans le Top 7 demandé. |
| `validate_production_secrets()` non appelé | **Réel** (`core/settings.py` L70-75, jamais invoqué dans `main.py`) — item **#8**, **Haute** ops. |

---

## Non-objectifs de ce document

- Aucune modification de code effectuée.
- Aucun test d’intrusion dynamique (Burp, XSS live) — validation **statique** uniquement.
- Estimations supposent un développeur familier du dépôt ; CI/tests complets peuvent ajouter une demi-journée.

---

*Généré par validation technique post-audit — Plateforme Santé Guinée.*
