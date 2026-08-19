# Catégories modifiables et solde d'ouverture

**Lot** : 2 | **Date** : 2026-08-19

## Catégories

La liste par défaut est rétablie, et l'API gagne modification, archivage et suppression.

- La **nature** (dépense / revenu) n'est pas modifiable : la changer inverserait le signe
  attendu de toutes les opérations déjà classées dessous, et donc les totaux de mois
  déjà clos.
- Supprimer une catégorie **utilisée** est refusé en 409, avec un message qui propose
  l'archivage. La base refuserait de toute façon (`ondelete=RESTRICT`) — le contrôle
  applicatif existe pour donner une explication, pas pour remplacer la contrainte.

## Solde d'ouverture

Au premier lancement, l'utilisateur peut saisir le solde actuel de son compte. Il est
enregistré comme une **opération d'ouverture**, pas comme une colonne `solde_initial` :
un solde reste une somme d'opérations, sans quoi on créerait la seconde source de vérité
que tout le projet évite.

L'opération porte `est_ouverture`, ce qui l'exclut des dépenses de période — un découvert
de départ n'est pas une dépense du mois, et l'y inclure ferait sauter tous les plafonds
dès la création du compte. C'est une **troisième dimension** de la table d'agrégats,
exhaustive et testée comme les deux premières.

## Vérifié

Témoin exécuté : en passant `INCLUT_OUVERTURES[DEPENSES_DE_PERIODE]` à `True`, deux tests
rougissent — un unitaire et un d'intégration. Plus un volet inverse : une ouverture
créditrice ne doit pas non plus *réduire* les dépenses.
