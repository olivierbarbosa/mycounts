# Prompt — Implémentation d’un système d’enveloppes et de projets budgétaires

Tu dois concevoir et implémenter dans une application de gestion budgétaire un système d’**enveloppes virtuelles**, de **projets d’épargne**, de **préparation mensuelle des allocations**, de **déclarations de virements** et de **rapprochement bancaire**.

L’objectif principal est de séparer strictement quatre réalités :

1. **Le budget prévu** : ce que l’on souhaite financer ce mois.
2. **L’affectation logique** : à quoi l’argent est réservé.
3. **Le mouvement bancaire déclaré** : ce que l’utilisateur indique avoir viré.
4. **La réalité bancaire** : ce que les comptes/relevés bancaires confirment réellement.

La règle fondamentale est :

```text
Compte bancaire ≠ Enveloppe ≠ Projet ≠ Budget mensuel
```

Une allocation vers une enveloppe ou un projet ne doit **jamais créer automatiquement une transaction bancaire**.

---

## 1. Comptes bancaires

Un compte bancaire représente uniquement **où l’argent se trouve physiquement**.

Exemples :

- compte courant ;
- compte épargne ;
- espèces ;
- compte joint ;
- autre compte financier.

Le solde bancaire doit rester indépendant des enveloppes et projets.

Une enveloppe peut éventuellement référencer un `preferred_account_id` afin d’indiquer sur quel compte son argent devrait idéalement être stocké.

Ce champ est uniquement une **préférence de couverture**.

Il ne doit provoquer aucun mouvement bancaire automatique.

---

## 2. Enveloppes virtuelles

Une enveloppe représente une **affectation logique d’argent**.

Exemples :

- Courses ;
- Vêtements ;
- Vacances ;
- Entretien voiture ;
- Ski ;
- Argent enfant ;
- Réserve annuelle.

Une enveloppe peut contenir au minimum :

```text
household_id
name
type
purpose
owner_user_id
preferred_account_id
category_id
target_amount
target_date
rollover_mode
is_active
created_by
```

### Types d’enveloppes

Prévoir par exemple :

```text
household
personal
child
reserve
```

### Usage / purpose

Distinguer au minimum :

```text
operating
reserve
```

- `operating` : dépenses courantes / fonctionnement ;
- `reserve` : argent mis de côté, réserve ou objectif.

---

## 3. Ledger des enveloppes

Ne jamais stocker directement un champ de type :

```text
current_balance
```

Le solde doit toujours être recalculé à partir d’un ledger.

Créer une table de mouvements d’enveloppe :

```text
EnvelopeMovement
```

avec des types tels que :

```text
initial_allocation
allocation
child_allowance
expense
refund
transfer_in
transfer_out
adjustment_in
adjustment_out
release
```

Tous les montants sont positifs.

C’est le type du mouvement qui indique s’il crédite ou débite l’enveloppe.

La logique de calcul est :

```text
solde =
    initial_allocation
  + allocation
  + child_allowance
  + refund
  + transfer_in
  + adjustment_in

  - expense
  - transfer_out
  - adjustment_out
  - release
```

Le ledger est la source de vérité.

Ne jamais modifier artificiellement un solde existant.

Exemple :

Au lieu de faire :

```text
balance = balance - 50
```

créer :

```text
expense = 50
```

Cela permet de conserver un historique complet et auditable.

---

## 4. Dépassement d’enveloppe

Une enveloppe doit pouvoir devenir négative.

Exemple :

```text
Solde enveloppe : 100 €
Dépense : 130 €

Nouveau solde : -30 €
```

Une dépense réelle ne doit jamais être bloquée simplement parce que l’enveloppe est insuffisamment financée.

En revanche, pour calculer le total d’argent réservé globalement, ne compter que les soldes positifs :

```text
reserved_total = somme(max(envelope_balance, 0))
```

Une enveloppe négative ne doit pas diminuer artificiellement l’argent réservé dans les autres enveloppes.

---

## 5. Lien entre enveloppes et budget mensuel

Une enveloppe peut être liée à une catégorie budgétaire.

Exemple :

```text
Catégorie : Vacances
Budget mensuel : 300 €

Enveloppe Vacances
Cible : 3 000 €
Solde actuel : 1 900 €
```

La préparation mensuelle doit calculer :

```text
space = max(0, target - current)

recommended = min(monthly_budget, space)

released = monthly_budget - recommended
```

Exemple :

```text
Cible : 3 000 €
Actuel : 2 900 €
Budget mensuel : 300 €

recommended = 100 €
released = 200 €
```

Les 200 € libérés ne doivent pas être automatiquement déplacés ailleurs.

L’application doit simplement les présenter comme disponibles pour :

- une autre enveloppe ;
- un projet ;
- un reliquat libre.

Si la cible ou le budget mensuel est indéfini, ne jamais inventer de montant.

---

## 6. Projets d’épargne

Un projet représente un objectif financier structuré.

Exemples :

- Ski décembre 2026 ;
- Voyage Japon ;
- Nouvelle voiture ;
- Travaux maison ;
- Nouveau PC.

Un projet peut contenir :

```text
household_id
name
type
owner_user_id
envelope_id
target_amount
target_date
monthly_contribution_cents
priority
status
description
created_by
```

Le projet doit obligatoirement être associé à une enveloppe de type réserve.

Relation :

```text
Project
   |
   └── Envelope
         purpose = reserve
```

Une enveloppe ne doit pouvoir être associée qu’à un seul projet.

Si un projet est créé sans enveloppe existante, créer automatiquement son enveloppe de réserve.

---

## 7. Ledger des projets

Les projets doivent avoir leur propre ledger :

```text
ProjectLedgerEntry
```

Types possibles :

```text
allocation
contribution
withdrawal
reallocation_in
reallocation_out
correction
funded_expense
```

Les montants sont positifs.

Le type définit crédit ou débit.

Le ledger du projet est la source de vérité du financement du projet.

Le solde projet est :

```text
project_balance =
    crédits du ledger
    - débits du ledger
```

Ne pas stocker de solde courant directement.

---

## 8. Compatibilité avec une enveloppe de réserve

Le projet reste lié à une enveloppe de réserve afin de conserver :

- la représentation logique globale ;
- la couverture par compte bancaire ;
- la compatibilité avec les transferts entre enveloppes ;
- le suivi par compte préféré.

Lorsqu’un montant est ajouté à un projet, il est acceptable de conserver deux traces cohérentes :

```text
EnvelopeMovement : allocation +300 €
ProjectLedger     : contribution +300 €
```

Mais il faut définir clairement lequel des deux ledgers est la source de vérité pour chaque fonctionnalité.

Pour les projets nouveaux, utiliser le `ProjectLedger` comme source principale de leur progression.

---

## 9. Calcul de progression d’un projet

Pour chaque projet :

```text
remaining = max(0, target - current)
```

Progression :

```text
progress = current / target * 100
```

Si une date cible existe :

```text
months_remaining = nombre de mois budgétaires restants
```

Avec au minimum 1 mois.

Contribution théorique :

```text
recommended_monthly_contribution =
    ceil(remaining / months_remaining)
```

Cette valeur est indicative.

Elle ne doit pas forcément être utilisée comme allocation réelle si le projet est lié à un budget mensuel spécifique.

---

## 10. Source de financement mensuel d’un projet

Un projet peut être financé de deux manières.

### Cas 1 — catégorie budgétaire liée

Si l’enveloppe du projet possède une catégorie avec un budget mensuel :

```text
source = category_monthly_budget
```

### Cas 2 — aucun budget lié

Utiliser :

```text
source = monthly_contribution_cents
```

comme valeur de secours.

Ne jamais additionner les deux.

Donc :

```text
if category exists:
    source = category budget
else:
    source = fallback monthly contribution
```

Puis :

```text
recommended = min(source, remaining)
```

Si une catégorie est liée mais que son budget du mois n’est pas défini, retourner un état explicite « budget indéfini ».

Ne jamais utiliser silencieusement le fallback dans ce cas.

---

## 11. Préparation mensuelle

Créer une notion dédiée :

```text
MonthlyFundingPreparation
```

Cette préparation doit calculer l’ensemble des besoins du mois sans encore effectuer de mouvement bancaire.

Workflow :

```text
Budgets du mois
      ↓
Calcul des enveloppes
      ↓
Calcul des projets
      ↓
Regroupement par compte de stockage
      ↓
Validation des allocations
      ↓
Déclaration éventuelle des virements
      ↓
Confirmation par la banque
```

La préparation doit stocker un snapshot du calcul afin de conserver l’état exact du mois au moment de la validation.

Exemple de champs :

```text
household_id
year
month
status
envelope_total_cents
project_total_cents
released_total_cents
snapshot
calculated_at
validated_at
validated_by
```

États possibles :

```text
calculated
validated
```

---

## 12. Calcul des enveloppes pendant la préparation

Pour chaque enveloppe éligible :

```text
current
target
monthly_budget
space
recommended
released
excess
progress
preferred_account
```

Formules :

```text
space = max(0, target - current)

recommended =
    target et budget connus
        ? min(monthly_budget, space)
        : 0

released =
    target et budget connus
        ? max(0, monthly_budget - recommended)
        : 0

excess =
    target connu
        ? max(0, current - target)
        : 0
```

---

## 13. Calcul des projets pendant la préparation

Pour chaque projet actif :

```text
current
target
remaining
target_date
monthly_budget
fallback_contribution
funding_source
recommended
released
progress
preferred_account
```

Formule :

```text
remaining = max(0, target - current)

source =
    catégorie liée
        ? budget catégorie
        : fallback

recommended =
    source connu
        ? min(source, remaining)
        : 0
```

Si le projet atteint son objectif :

```text
recommended = 0
```

Le budget normalement destiné au projet devient alors disponible pour une autre affectation.

---

## 14. Validation des allocations

Avant validation, la préparation n’est qu’une simulation.

Exemple :

```text
Vacances    +200 €
Ski         +300 €
Voiture     +100 €
-----------------
Total       +600 €
```

Lors de la validation :

- créer les mouvements d’enveloppes ;
- créer les contributions projets ;
- ne créer aucune transaction bancaire.

La validation doit être transactionnelle et idempotente.

Utiliser des références uniques du type :

```text
monthly-funding:{preparation_id}:envelope:{envelope_id}

monthly-funding:{preparation_id}:project:{project_id}
```

Une double validation ne doit jamais doubler les montants.

---

## 15. Virement bancaire déclaré

Après validation des allocations, l’utilisateur peut réellement déplacer l’argent entre ses comptes.

Créer une notion distincte :

```text
MonthlyFundingTransferDeclaration
```

Elle représente :

> L’utilisateur déclare avoir effectué ce virement.

Exemple :

```text
Source : compte courant
Destination : compte épargne
Montant : 1 925 €
Date : 20/08/2026
```

Cette déclaration ne doit créer aucune transaction bancaire automatique.

Elle constitue seulement une intention / déclaration en attente de confirmation.

Prévoir :

```text
monthly_funding_preparation_id
source_account_id
destination_account_id
amount_cents
transfer_date
declared_at
declared_by
bank_confirmed_at
bank_transaction_id
```

---

## 16. Solde théorique attendu d’un compte

Grâce au `preferred_account_id` des enveloppes et projets, calculer combien devrait théoriquement se trouver sur chaque compte.

Exemple :

```text
Compte épargne

Vacances       600 €
Ski          1 200 €
Voiture        500 €
Réserve        400 €
-------------------
Attendu       2 700 €
```

Puis comparer :

```text
bank_balance = 2 500 €
expected     = 2 700 €

delta = -200 €
```

Prévoir des états tels que :

```text
correct
excess
insufficient
pending
confirmed
```

---

## 17. Confirmation bancaire

Une déclaration de virement ne devient confirmée que lorsque :

- une transaction bancaire correspondante est rapprochée ;
- ou un relevé bancaire fiable permet d’établir que le compte couvre désormais le montant théorique attendu.

Le système doit donc distinguer :

```text
allocation validée
≠
virement déclaré
≠
virement confirmé
```

Workflow cible :

```text
1. À préparer
      ↓
2. Préparation calculée
      ↓
3. Allocations validées
      ↓
4. Virement effectué / déclaré
      ↓
5. Confirmé par la banque
```

---

## 18. Gestion d’un projet terminé ou abandonné

Un projet doit pouvoir être :

```text
active
paused
completed
cancelled
```

### Projet terminé

Atteindre l’objectif ne doit pas automatiquement vider l’enveloppe ni déplacer les fonds.

Le projet peut être marqué terminé tout en conservant l’historique.

### Projet abandonné

Si des fonds sont présents, demander explicitement quoi en faire.

Options :

```text
transfer
release
```

`transfer` :

```text
ancienne enveloppe : transfer_out
nouvelle enveloppe : transfer_in
```

`release` :

```text
ancienne enveloppe : release
```

Ne jamais supprimer silencieusement l’historique.

---

## 19. Rollover des enveloppes

Prévoir un comportement de fin de mois :

```text
ask
rollover
release
```

- `rollover` : conserve le solde ;
- `release` : libère le reliquat ;
- `ask` : demande explicitement à l’utilisateur.

Un transfert logique entre enveloppes doit créer :

```text
transfer_out
transfer_in
```

mais aucune transaction bancaire.

---

## 20. Contraintes importantes

Respecter impérativement les règles suivantes.

### Historique

Ne jamais réécrire l’histoire financière lorsque ce n’est pas nécessaire.

Préférer :

```text
adjustment
refund
correction
transfer
release
```

à la modification destructive de mouvements passés.

### Idempotence

Toute action pouvant être soumise deux fois doit disposer d’une clé unique stable.

### Transactions DB

Les opérations combinées doivent être atomiques.

Exemple :

```text
transfer_out + transfer_in
```

doivent être créés dans une même transaction DB.

### Montants

Ne jamais utiliser de `float`.

Utiliser :

```text
integer cents
```

ou un type décimal exact.

### Séparation logique / bancaire

Ne jamais créer une transaction bancaire à partir :

- d’une allocation ;
- d’une contribution projet ;
- d’un transfert entre enveloppes ;
- d’une préparation mensuelle.

---

## 21. Modèle conceptuel cible

```text
Account
  └── argent physique

Envelope
  ├── affectation logique
  ├── cible éventuelle
  ├── compte préféré
  └── EnvelopeMovement[]
        └── source de vérité du solde enveloppe

Project
  ├── objectif
  ├── échéance
  ├── priorité
  ├── enveloppe de réserve associée
  └── ProjectLedgerEntry[]
        └── source de vérité du financement projet

MonthlyBudget
  └── ce que l’on souhaite provisionner ce mois

MonthlyFundingPreparation
  └── calcule les allocations recommandées

MonthlyFundingTransferDeclaration
  └── indique qu’un virement bancaire est déclaré effectué

BankTransaction / BankImport
  └── confirme la réalité bancaire
```

---

## 22. Architecture fonctionnelle à conserver absolument

```text
PLANNING
Budget mensuel
      ↓

AFFECTATION LOGIQUE
Envelope / Project ledgers
      ↓

INTENTION BANCAIRE
Déclaration de virement
      ↓

RÉALITÉ BANCAIRE
Compte / transaction / import
```

Ces quatre niveaux ne doivent jamais être fusionnés.

L’application doit être capable de répondre à tout moment à quatre questions différentes :

```text
Combien avais-je prévu de mettre de côté ?

Combien ai-je logiquement réservé ?

Combien ai-je déclaré avoir transféré ?

Combien la banque confirme réellement ?
```

---

## 23. Résultat attendu

Implémenter une architecture :

- traçable ;
- idempotente ;
- auditable ;
- sans double comptage ;
- sans solde mutable servant de source de vérité ;
- avec séparation stricte entre logique budgétaire et réalité bancaire ;
- capable de calculer le solde théorique attendu sur chaque compte ;
- capable de gérer enveloppes, projets, objectifs, dépassements, reliquats et rapprochement bancaire.

Avant de coder, commence par :

1. proposer le modèle de données ;
2. identifier les invariants métier ;
3. définir les services responsables de chaque calcul ;
4. définir les événements / mouvements de ledger ;
5. définir le workflow mensuel ;
6. seulement ensuite proposer l’implémentation.
