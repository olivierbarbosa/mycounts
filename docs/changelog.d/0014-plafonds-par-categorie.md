# Plafonds par catégorie (lot 4, backend)

**Lot** : 4 | **Date** : 2026-08-19

Une limite par catégorie, mesurée sur la **période budgétaire de paie à paie** — pas sur
le mois civil.

## Deux grandeurs qui ne se mélangent jamais

- **consommé** : ce qui est déjà sorti (confirmé ou à confirmer) ;
- **à venir** : les échéances récurrentes prévues d'ici la fin de période.

Les additionner sous le nom de « dépensé » donnerait un chiffre plus complet mais faux à
lire : annoncer 380 € dépensés alors que 150 € ne sont pas encore partis est exactement la
confusion qui fait cesser de croire l'outil. L'interface peut montrer les deux, jamais
leur somme sous une seule étiquette.

En revanche, `depasse_avec_les_echeances` combine les deux **explicitement** : c'est
l'alerte réellement utile — être à 300 € sur 400 paraît confortable jusqu'à savoir que
150 € tombent avant la fin de la période.

## Détails de calcul

- Le pourcentage est un **entier tronqué**, jamais un flottant ni un arrondi : à 99,7 % on
  affiche 99, donc l'interface n'annonce jamais « 100 % » avant que la limite soit
  réellement atteinte.
- Un **revenu** sur la catégorie ne réduit pas la consommation : sinon un remboursement
  encaissé ferait disparaître des dépenses réelles du suivi.
- Un **solde d'ouverture** ne consomme aucun plafond.
- Une opération **sans catégorie** n'en consomme aucun non plus : l'imputer au hasard
  fausserait silencieusement le suivi.
- Les plafonds sont **personnels** : voir celui de l'autre membre reviendrait à voir ses
  intentions de dépense.

## Vérifié

18 tests unitaires, 11 d'intégration. Deux témoins exécutés contre leur implémentation
fautive : fondre l'à-venir dans le consommé fait rougir 2 tests, arrondir le pourcentage
au lieu de le tronquer en fait rougir 2 autres.
