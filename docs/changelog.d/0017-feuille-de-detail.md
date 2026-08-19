# Feuille de détail d'une opération

**Date** : 2026-08-19

Taper une ligne de l'accueil ouvre une feuille montant depuis le bas — même mécanique que
la saisie, donc rien de nouveau à apprendre, et c'est le geste naturel sur téléphone.

Elle affiche la date complète, le compte, l'état et surtout l'**origine** : saisie
manuelle, prélèvement automatique ou solde d'ouverture. Sans elle, impossible de savoir
pourquoi une ligne est apparue sans qu'on l'ait saisie.

## Ce qui se corrige, et ce qui ne se corrige pas

Libellé, montant, date et catégorie se corrigent. Le compte et le caractère de paie, non —
et l'écran le **dit** au lieu de laisser chercher le champ manquant.

Le sens ne change jamais : une dépense reste une dépense, quel que soit le montant saisi.
Le faire basculer par un signe tapé serait une inversion silencieuse, invisible jusqu'au
solde suivant.

## Suppression

Confirmation systématique. Le message diffère selon l'origine : pour une échéance de
prélèvement, il précise qu'elle est écartée définitivement **sans réapparaître au prochain
calcul**, et que le prélèvement lui-même continue.

## Vérifié

6 tests de bout en bout, dont celui qui rejoue trois fois le calcul après le retrait d'une
échéance : elle ne revient pas. Toute la ligne est cliquable — viser une petite zone dans
une ligne est le meilleur moyen de rater son geste sur téléphone.
