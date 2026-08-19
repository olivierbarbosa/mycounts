# Calendrier des prélèvements (lot 3)

**Lot** : 3 | **Date** : 2026-08-19

L'écran « Agenda » devient **Calendrier** et ne traite plus que des **charges** : un revenu
se saisit depuis l'accueil. Sa raison d'être tient en trois points — ajouter un
prélèvement, voir d'un coup d'œil qui prélève et quand, couvrir tous les rythmes.

## Grille mensuelle, sur toutes les tailles

Sept colonnes, six semaines, toujours 42 cases : une grille de hauteur variable ferait
sauter tout ce qui la suit à chaque changement de mois.

Sous 600 px, les libellés cèdent la place à des **points** et taper une case révèle le
détail du jour en dessous. Sept colonnes sur 390 px donnent des cases de 48 px : assez
pour un numéro et des points, pas pour un mot.

## Rythmes nommés

Mensuel, trimestriel, semestriel, annuel, hebdomadaire, quinzaine, plus un mode libre. Le
moteur gérait déjà tous les cas ; ce qui manquait était de les **nommer** — personne ne
traduit « tous les 3 mois » en « intervalle 3, unité mois » sans hésiter, et une
hésitation à la saisie finit en prélèvement mal daté.

## Modifier, ajouter, supprimer

Une modification ne réécrit **pas** les prélèvements déjà passés : un abonnement dont le
tarif augmente n'a pas coûté davantage les mois précédents. Réécrire l'historique ferait
changer des soldes de mois clos. Rouvrir un prélèvement trimestriel réaffiche « tous les
3 mois » et non le rythme par défaut — une modification qu'on n'a pas demandée est pire
qu'un champ vide.

Le compte n'est pas modifiable : déplacer un prélèvement changerait deux soldes
rétroactivement. On arrête et on recrée.

## Pastilles de marque plutôt que logos

`simple-icons` ne contient que **7 marques sur 18** d'abonnements courants en France, pour
25 Mo — Free, SFR, EDF, Canal+, Amazon Prime en sont absents. Remplacé par des pastilles
générées : initiale et teinte stable dérivée du nom. Couverture 100 %, zéro dépendance, et
surtout **toujours présentes** — pas de trous au milieu d'un calendrier.

## Icônes

`lucide-react`, tree-shakable : +8 ko gzip. Les glyphes Unicode ont disparu — un caractère
change de dessin selon la police du système et ne s'aligne jamais deux fois pareil.
