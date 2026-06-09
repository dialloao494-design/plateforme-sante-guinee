# Guide utilisateur — Médecin

**Plateforme Santé Guinée**  
**Public :** praticiens de santé (médecins généralistes, spécialistes)  
**Accès :** navigateur web (Chrome, Firefox, Edge — version récente)

---

## 1. Première connexion

### 1.1 Créer un compte médecin

1. Ouvrir l'URL de la plateforme (ex. `https://staging.sante.gn` ou `http://localhost:8088`).
2. Cliquer sur **S'inscrire** / **Créer un compte**.
3. Remplir le formulaire :
   - prénom, nom ;
   - adresse e-mail professionnelle ;
   - mot de passe (8 caractères minimum, majuscule + chiffre recommandés) ;
   - rôle : **Médecin** ;
   - spécialité (ex. Cardiologie, Médecine générale) ;
   - ville / lieu d'exercice.
4. Valider → vous êtes redirigé vers la page de connexion.
5. Se connecter avec e-mail + mot de passe.

> **Note :** l'inscription publique crée un profil médecin. La vérification d'identité professionnelle (ordre des médecins) n'est pas encore automatisée — prévue en phase post-pilote.

### 1.2 Se connecter

1. Aller sur **Connexion**.
2. Saisir e-mail et mot de passe.
3. Après connexion → **Tableau de bord médecin** (`/doctor/dashboard`).

### 1.3 Comptes démo (environnement pilote)

| Email | Mot de passe |
|-------|--------------|
| `dr.mamady@example.com` | `Doctor123!` |
| `dr.amu@example.com` | `Doctor123!` |
| `dr.souleimane@example.com` | `Doctor123!` |
| `dr.fatou@example.com` | `Doctor123!` |

---

## 2. Tableau de bord médecin

**Menu :** Tableau de bord · Mes rendez-vous · Messages · Patients

Le tableau de bord affiche :

- rendez-vous du jour et à venir ;
- consultations en attente de paiement ;
- accès rapide à la téléconsultation ;
- notifications récentes.

---

## 3. Gestion des disponibilités

Les patients ne peuvent réserver que dans vos créneaux déclarés.

### 3.1 Comprendre le modèle

- Disponibilités = plages horaires par **jour de la semaine** (0 = lundi, 6 = dimanche).
- Exemple : Lundi 09:00–12:00, Mardi 09:00–12:00.
- Minimum recommandé pilote : **5 créneaux** (lun–ven matin).

### 3.2 Consulter son planning

1. Aller dans **Mon profil** ou **Paramètres médecin** (selon version UI).
2. Section **Disponibilités** → liste des créneaux actifs.

Via API (support technique) :

```
GET /api/doctors/{votre_id}/availability
```

### 3.3 Ajouter un créneau

1. Cliquer **Ajouter une disponibilité**.
2. Choisir :
   - jour de la semaine ;
   - heure de début (ex. 09:00) ;
   - heure de fin (ex. 12:00).
3. Enregistrer.

Règles :

- l'heure de fin doit être **après** l'heure de début ;
- les rendez-vous existants ne sont pas déplacés automatiquement ;
- désactiver un créneau (`is_active=false`) empêche de nouvelles réservations sans supprimer l'historique.

### 3.4 Bonnes pratiques pilote

- Déclarer vos créneaux **avant** d'inviter des patients.
- Prévoir 30 min par téléconsultation (durée par défaut).
- Bloquer les jours de congé en désactivant les créneaux concernés.

---

## 4. Gestion des rendez-vous

### 4.1 Voir ses rendez-vous

**Menu → Mes rendez-vous** (`/doctor/appointments`)

Filtres : à venir, en cours, terminés, annulés.

Informations affichées :

- nom du patient ;
- date et heure ;
- type (physique / téléconsultation) ;
- statut paiement ;
- statut (pending, confirmed, completed, cancelled).

### 4.2 Actions sur un rendez-vous

| Action | Quand |
|--------|-------|
| **Rejoindre la téléconsultation** | RDV payé + dans la fenêtre horaire (15 min avant) |
| **Ouvrir la messagerie** | À tout moment après création du RDV |
| **Voir le dossier patient** | Patient lié par au moins 1 RDV |
| **Marquer terminé** | Après la consultation |

---

## 5. Consultation du dossier patient

**Menu → Patients** ou clic sur un patient depuis un RDV  
**Route :** `/doctor/patient/{id}`

### 5.1 Prérequis

Un dossier patient n'est accessible que si vous avez **au moins un rendez-vous** avec ce patient. Sans lien RDV → accès refusé.

### 5.2 Contenu du dossier

| Section | Description |
|---------|-------------|
| **Informations** | Nom, âge, coordonnées |
| **Notes cliniques** | Comptes rendus de consultation |
| **Synthèses** | Diagnostic, traitement, recommandations |
| **Documents** | Ordonnances, résultats uploadés |
| **Timeline** | Historique chronologique unifié |
| **Rendez-vous** | Historique des consultations |

### 5.3 Créer une note clinique

1. Ouvrir le dossier patient.
2. Section **Notes** → **Nouvelle note**.
3. Remplir :
   - **Type** : consultation / suivi / urgence ;
   - **Contenu** : observations cliniques ;
   - **Rendez-vous lié** (optionnel) : sélectionner le RDV en cours.
4. Enregistrer.

La note est horodatée et signée avec votre identité médecin.

### 5.4 Upload d'un document

1. Section **Documents** → **Ajouter un document**.
2. Choisir le **type** (ordonnance, résultat labo, imagerie…).
3. Sélectionner le fichier (PDF, JPEG, PNG — max 10 Mo).
4. Envoyer.

Le document est stocké de manière sécurisée ; le patient peut le consulter depuis son espace.

---

## 6. Création d'une synthèse clinique

La synthèse formalise le compte rendu post-consultation.

### 6.1 Quand créer une synthèse

- En fin de téléconsultation ou consultation physique ;
- Avant de clôturer le rendez-vous ;
- Pour transmettre au patient diagnostic et conduite à tenir.

### 6.2 Étapes

1. Ouvrir le dossier patient (`/doctor/patient/{id}`).
2. Section **Synthèses** → **Nouvelle synthèse**.
3. Remplir au minimum un des champs :
   - **Diagnostic** : ex. « HTA grade 1, contrôlée » ;
   - **Traitement** : ex. « Amlodipine 5 mg, 1 cp/j le matin » ;
   - **Recommandations** : ex. « Contrôle tensionnel dans 15 jours, régime hyposodé ».
4. Lier au rendez-vous en cours (recommandé).
5. Enregistrer.

### 6.3 Bonnes pratiques

- Rédiger des synthèses **compréhensibles par le patient**.
- Éviter les abréviations médicales non expliquées.
- Vérifier l'orthographe des molécules prescrites.

---

## 7. Téléconsultation

### 7.1 Prérequis côté patient

Le patient doit avoir **payé** le rendez-vous avant de pouvoir rejoindre la salle.

### 7.2 Rejoindre une téléconsultation

1. **Mes rendez-vous** → repérer le RDV téléconsultation.
2. Cliquer **Rejoindre** (actif 15 min avant l'heure prévue).
3. Autoriser **caméra** et **micro** dans le navigateur.
4. Attendre le patient dans la salle Jitsi embarquée.

**URL directe :** `/consultation/{id_du_rendez_vous}`

### 7.3 Pendant la consultation

- Vérifier l'identité du patient (nom affiché).
- Utiliser le chat Jitsi si la connexion audio est faible.
- Prendre des notes dans le dossier patient (onglet séparé).

### 7.4 Terminer la session

1. Cliquer **Terminer la consultation** dans l'interface.
2. Le statut RDV passe à **completed**.
3. Créer la synthèse clinique (section 6).

### 7.5 Problèmes fréquents

| Problème | Solution |
|----------|----------|
| Bouton « Rejoindre » grisé | Patient n'a pas payé, ou hors fenêtre horaire |
| Caméra bloquée | Vérifier permissions navigateur ; utiliser HTTPS |
| Pas de son | Tester micro dans paramètres OS ; recharger la page |
| Patient absent | Attendre 10 min ; contacter via messagerie RDV |

---

## 8. Messagerie

**Route :** `/messages/{id_rendez_vous}`

- Échanges texte entre vous et le patient **dans le contexte d'un RDV**.
- Possibilité d'envoyer une pièce jointe (document clinique chiffré).
- Historique conservé côté serveur.

> La messagerie ne remplace pas une consultation urgente. En cas d'urgence vitale, orienter le patient vers les services d'urgence.

---

## 9. Notifications

**Menu → Notifications** (`/notifications`)

Alertes reçues :

- nouveau rendez-vous ;
- paiement confirmé ;
- message patient ;
- rappel téléconsultation imminente.

---

## 10. Sécurité et confidentialité

- **Déconnexion** : utiliser le bouton Déconnexion en fin de session sur poste partagé.
- **Mot de passe** : ne pas le partager ; le changer en cas de doute.
- **Dossier patient** : chaque accès est **journalisé** (audit trail) — ne consultez que les dossiers de vos patients.
- **Secret médical** : ne pas capturer d'écran de consultation sans consentement.

---

## 11. Support

| Besoin | Contact |
|--------|---------|
| Problème technique plateforme | Support IT / administrateur plateforme |
| Mot de passe oublié | Procédure reset (administrateur) |
| Question sur un paiement patient | Support administratif |

---

## 12. Raccourcis utiles

| Action | URL |
|--------|-----|
| Tableau de bord | `/doctor/dashboard` |
| Mes RDV | `/doctor/appointments` |
| Dossier patient | `/doctor/patient/{id}` |
| Téléconsultation | `/consultation/{id_rdv}` |
| Messages | `/messages/{id_rdv}` |
