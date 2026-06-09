# Guide utilisateur — Patient

**Plateforme Santé Guinée**  
**Public :** patients utilisant la plateforme pour consulter à distance ou prendre rendez-vous  
**Accès :** navigateur web (ordinateur, tablette, smartphone)

---

## 1. Première utilisation

### 1.1 Créer un compte

1. Ouvrir l'URL de la plateforme.
2. Cliquer **S'inscrire** / **Créer un compte**.
3. Remplir :
   - prénom et nom ;
   - adresse e-mail ;
   - mot de passe (8 caractères minimum) ;
   - rôle : **Patient**.
4. Valider → retour à la page de connexion.
5. Se connecter.

### 1.2 Se connecter

1. **Connexion** → saisir e-mail et mot de passe.
2. Redirection vers **Mon tableau de bord** (`/dashboard`).

### 1.3 Compte démo (environnement pilote)

| Email | Mot de passe |
|-------|--------------|
| `test.patient@example.com` | `Patient123!` |

---

## 2. Tableau de bord

Après connexion, vous accédez à :

- vos prochains rendez-vous ;
- rappels de téléconsultation ;
- notifications (paiement, messages) ;
- liens rapides vers l'annuaire médecins.

---

## 3. Trouver un médecin

### 3.1 Annuaire

**Menu → Médecins** (`/doctors`)

Informations affichées :

- nom et spécialité ;
- ville / lieu de consultation ;
- tarif indicatif ;
- disponibilités (créneaux ouverts).

### 3.2 Fiche médecin

Cliquer sur un médecin → `/doctors/{id}`

Vous y trouvez :

- présentation ;
- spécialité ;
- tarif de consultation ;
- bouton **Prendre rendez-vous**.

---

## 4. Prendre un rendez-vous

**Menu → Mes rendez-vous** → **Nouveau rendez-vous**  
ou depuis la fiche médecin.

### 4.1 Étapes

1. **Choisir le médecin** (si pas déjà sélectionné).
2. **Type de consultation** :
   - **Physique** — au cabinet / centre de santé ;
   - **Téléconsultation** — consultation vidéo à distance.
3. **Choisir la date et l'heure** parmi les créneaux disponibles.
4. **Durée** : 30 minutes (par défaut).
5. Confirmer → le rendez-vous est créé avec statut **En attente de paiement**.

### 4.2 Règles importantes

- Vous ne pouvez réserver que dans les **créneaux ouverts** du médecin.
- Un créneau déjà pris par un autre patient n'est plus disponible.
- La téléconsultation nécessite un **paiement** avant d'accéder à la salle vidéo.

### 4.3 Annuler un rendez-vous

1. **Mes rendez-vous** → sélectionner le RDV.
2. Cliquer **Annuler** (si disponible).
3. Confirmer.

Les conditions de remboursement dépendent de la politique de la plateforme (Stripe).

---

## 5. Paiement

### 5.1 Quand payer

Dès la création du rendez-vous, celui-ci apparaît comme **Non payé**.  
Le paiement débloque :

- la confirmation définitive du RDV ;
- l'accès à la téléconsultation (si applicable).

### 5.2 Payer en ligne (Stripe)

1. **Mes rendez-vous** → RDV non payé → **Payer**.
2. Redirection vers la page de paiement sécurisée **Stripe**.
3. Saisir les informations carte (mode test en pilote : cartes Stripe test).
4. Après paiement réussi → redirection vers `/success`.
5. Statut RDV : **Confirmé · Payé**.

### 5.3 Cartes test Stripe (environnement pilote)

| Numéro | Résultat |
|--------|----------|
| `4242 4242 4242 4242` | Paiement réussi |
| `4000 0000 0000 0002` | Carte refusée |

Date expiration : toute date future · CVC : 3 chiffres quelconques.

### 5.4 Autres moyens de paiement

Orange Money et MTN MoMo sont prévus — **en cours de déploiement** (bêta).  
En pilote contrôlé, l'administrateur peut confirmer un paiement manuellement.

### 5.5 Problèmes de paiement

| Situation | Action |
|-----------|--------|
| Paiement refusé | Vérifier solde / contacter banque ; réessayer |
| Page blanche Stripe | Vérifier connexion internet ; changer navigateur |
| Payé mais statut « non payé » | Attendre 1–2 min ; rafraîchir ; contacter support |

---

## 6. Téléconsultation

### 6.1 Préparer sa consultation

**Matériel :**

- smartphone ou ordinateur avec caméra et micro ;
- connexion internet stable (4G/5G ou Wi-Fi) ;
- environnement calme et bien éclairé.

**Documents utiles :**

- ordonnances en cours ;
- résultats d'examens récents ;
- liste des médicaments pris.

### 6.2 Rejoindre la salle

1. **Mes rendez-vous** → RDV téléconsultation **payé**.
2. Le bouton **Rejoindre** s'active **15 minutes avant** l'heure prévue.
3. Cliquer **Rejoindre** → `/consultation/{id}`.
4. Autoriser caméra et micro quand le navigateur le demande.
5. Attendre l'arrivée du médecin dans la salle vidéo.

### 6.3 Pendant la consultation

- Parlez distinctement ; vérifiez que le micro n'est pas muet.
- Montrez documents à la caméra si le médecin le demande.
- Utilisez le chat intégré si l'audio est coupé.

### 6.4 Après la consultation

- Le médecin peut rédiger une **synthèse** visible dans votre historique.
- Consultez vos **documents** et **messages** post-consultation.
- Suivez les recommandations et traitements prescrits.

### 6.5 Dépannage téléconsultation

| Problème | Solution |
|----------|----------|
| « Paiement requis » | Finaliser le paiement d'abord |
| « Trop tôt » | Attendre l'ouverture (15 min avant) |
| Pas de vidéo | Autoriser caméra ; fermer autres apps utilisant la caméra |
| Connexion instable | Passer en 4G ; rapprocher du routeur Wi-Fi |

---

## 7. Messagerie avec le médecin

**Accès :** depuis un rendez-vous → **Messages** (`/messages/{id_rdv}`)

- Échange de messages texte avec votre médecin **dans le cadre d'un RDV**.
- Réception de documents (ordonnances PDF).
- **Ne pas utiliser** pour les urgences vitales.

**Urgences :** contacter le **142** (SAMU Guinée) ou vous rendre au centre de santé le plus proche.

---

## 8. Accès à l'historique médical

### 8.1 Ce que vous pouvez consulter

Depuis votre espace (selon version UI) :

| Donnée | Accès |
|--------|-------|
| Notes cliniques rédigées par le médecin | Lecture seule |
| Synthèses de consultation | Lecture seule |
| Documents uploadés (ordonnances…) | Lecture + téléchargement |
| Timeline | Historique chronologique |
| Rendez-vous passés | Dates, médecins, statuts |

> Vous **ne pouvez pas** modifier ni supprimer les données cliniques — seul votre médecin ou l'administrateur le peut.

### 8.2 Télécharger un document

1. Accéder à votre dossier / historique.
2. Section **Documents**.
3. Cliquer sur le document → **Télécharger**.

### 8.3 Confidentialité

- Seuls **vous**, vos **médecins consultés** (via RDV) et les **administrateurs** autorisés accèdent à votre dossier.
- Chaque consultation du dossier est **enregistrée** (audit) pour votre protection.

---

## 9. Notifications

**Menu → Notifications**

Vous recevez des alertes pour :

- confirmation de rendez-vous ;
- rappel de paiement ;
- rappel téléconsultation (15 min avant) ;
- nouveau message du médecin ;
- document ajouté à votre dossier.

---

## 10. Gérer son compte

### 10.1 Profil

Informations modifiables (selon version) :

- coordonnées ;
- téléphone ;
- adresse ;
- contact d'urgence.

### 10.2 Mot de passe

- Choisir un mot de passe unique, non réutilisé ailleurs.
- Se déconnecter sur appareil partagé après usage.

### 10.3 Déconnexion

Menu utilisateur → **Déconnexion** (supprime la session locale).

---

## 11. Parcours complet (résumé)

```
Inscription → Connexion → Choisir médecin → Prendre RDV
    → Payer (Stripe) → [Jour J - 15 min] Rejoindre téléconsultation
    → Consultation → Recevoir synthèse / documents → Consulter historique
```

---

## 12. Support patient

| Besoin | Action |
|--------|--------|
| Problème technique | Contacter le support plateforme |
| Question sur un RDV | Messagerie du RDV ou support |
| Urgence médicale | **142** ou urgences hospitalières — pas la plateforme |
| Données personnelles (RGPD) | Demande auprès de l'administrateur plateforme |

---

## 13. Raccourcis

| Page | URL |
|------|-----|
| Tableau de bord | `/dashboard` |
| Médecins | `/doctors` |
| Mes rendez-vous | `/appointments` |
| Téléconsultation | `/consultation/{id_rdv}` |
| Messages | `/messages/{id_rdv}` |
| Notifications | `/notifications` |
