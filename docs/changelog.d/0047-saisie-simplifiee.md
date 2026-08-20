# Lot A — la saisie

## Le modal `+` ne montre plus que l'essentiel

Sept champs sous les yeux à chaque saisie : sens, montant, libellé, date, catégorie,
compte, case paie. Deux d'entre eux — la date et le compte — ne sont presque jamais
touchés : on saisit une dépense du jour, sur le compte courant.

Ils passent donc dans un repli, dont le libellé **affiche leurs valeurs** :
« Aujourd'hui · Compte courant ». Ce détail fait tout : un repli annonçant « Options »
obligerait à l'ouvrir pour vérifier, ce qui coûterait plus cher que les deux champs qu'il
remplace. Ici la vérification est gratuite et le geste n'est demandé qu'à qui change
vraiment quelque chose.

Le montant passe en grand, sans étiquette visible — c'est le seul champ dont personne ne se
demande ce qu'il attend. L'étiquette reste portée par `aria-label` : la retirer du DOM
l'aurait aussi retirée aux lecteurs d'écran, ce qui n'est pas la même simplification.

Cas courant : **trois champs, zéro dépliage**.

## « Virer de l'argent » ouvre un virement

Depuis l'Épargne, la feuille s'ouvre verrouillée sur Virement et sa bascule disparaît.
« Dépense » et « Revenu » y étaient deux options hors sujet dans une bascule à trois
positions, à relire à chaque ouverture.

Le sens imposé est un état de l'application, remis à zéro à chaque autre ouverture : sans
cela, le `+` de la barre serait resté verrouillé sur Virement pour le reste de la session.
C'est un test à part qui le vérifie.

## Les témoins

Quatre, tous vérifiés par mutation :

- le repli cache la date **et** en affiche la valeur ;
- changer la date se voit sur le repli — c'est celui-ci qui distingue un résumé CALCULÉ
  d'un libellé écrit en dur, et le premier test seul passait la mutation ;
- virer depuis l'Épargne n'offre ni dépense ni revenu ;
- le `+` de la barre rend la bascule après un passage par l'Épargne.
