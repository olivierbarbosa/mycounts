# Comptes, catégories, opérations et période budgétaire (lot 2, socle)

**Lot** : 2 | **Date** : 2026-08-19

## Modèle

Tables `compte`, `categorie`, `operation`, plus le réglage `paies_par_cycle` sur
l'utilisateur. Deux choix structurants :

- **`operation` ne porte pas de `foyer_id`.** Il serait une copie de `compte.foyer_id`,
  donc une seconde source de vérité qui dériverait au premier changement de compte. Le
  périmètre passe par une jointure — plus verbeux, impossible à désynchroniser.
- **La couleur d'une catégorie est une teinte nommée**, pas un code hexadécimal. Un hex en
  base contournerait le garde-fou n°9 et rendrait impossible l'adaptation clair/sombre.

## Période budgétaire

`domain/periode.py` : une période s'ouvre à la `date_operation` d'une paie, jamais au jour
de saisie. Avec `paies_par_cycle` > 1, seule une paie sur N ouvre un cycle. Tant que la
paie suivante n'est pas saisie, la fin est **estimée** et signalée comme telle.

Le piège des fins de mois est traité : le 31 janvier + un mois donne le 28 février, pas un
débordement sur mars. Sans ce rabattement, une paie du 31 produirait une période d'un seul
jour tous les deux mois.

## Vérifié

Trois témoins exécutés contre leur implémentation fautive :

- `ajouter_un_mois` remplacé par « +31 jours » → 5 tests rougissent ;
- la date de saisie introduite dans les bornes → 6 tests rougissent ;
- la règle de confidentialité retirée du repository → 4 tests rougissent.

Plus les contraintes vérifiées côté **moteur** et non côté Python : montant non nul, paie
positive, devise EUR, unicité du nom de compte, catégorie utilisée non supprimable. Une
validation applicative se contourne par un script ou un import ; la base, non.

Un constat mesuré et documenté plutôt que supposé : la colonne `etat` est un VARCHAR sans
contrainte d'énumération — PostgreSQL accepte une valeur inventée. C'est écrit dans le
test, à durcir si un import externe écrit un jour dans cette table.

Décisions par défaut ajoutées : D4 (mois civil sans paie), D5 (réglage sur l'utilisateur),
D6 (teintes nommées).
