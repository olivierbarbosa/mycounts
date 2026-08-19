# Écrans : amorçage, saisie, soldes et liste (lot 2)

**Lot** : 2 | **Date** : 2026-08-19

## Ce qui est livrable

Amorçage du premier compte avec le solde actuel, saisie d'une opération, affichage des
soldes de période et liste des opérations. Vérifié dans un vrai navigateur :
1 240,50 − 45,90 = 1 194,60, et l'ouverture n'entre pas dans les dépenses.

## Un préfixe `/api` unique

Toutes les routes sont montées sous `/api`. La liste des chemins à relayer vivait
auparavant dans `vite.config.ts` : c'était une seconde source de vérité face au routeur
FastAPI, et elle a divergé dès la première route ajoutée — `/comptes` renvoyait la page
HTML au lieu du JSON. Un seul préfixe, aucune liste à maintenir.

## Trois défauts d'affichage trouvés à l'écran

Aucun n'était détectable dans un test d'API :

- un solde affiché « +1 240,50 € » : le signe positif est du bruit sur un solde ;
- « Dépensé sur la période : +0,00 € » en vert — un zéro coloré en crédit laisse croire à
  une entrée d'argent qui n'a pas eu lieu ;
- « le 1 août » au lieu de « 1er août ».

## Contraste : deux essais mesurés avant le bon

La pastille de catégorie a échoué deux fois au seuil AA : initiale blanche sur aplat
coloré (1,92:1), puis teinte sur son propre halo (3,98:1 en thème clair). La couleur est
maintenant portée par le halo seul, le texte utilisant la couleur standard dont le
contraste est déjà vérifié.

## Tests de bout en bout : un état de départ fixé

Le `globalSetup` garantit désormais « un compte, aucune opération ». Sans cela, chaque
exécution mesurait un état cumulé et un locator qui attend une ligne en trouvait trois.
Le script de remise à zéro **refuse de s'exécuter** sur une adresse qui n'est pas un
compte de démonstration.

Conséquence assumée et écrite dans le script : l'écran d'amorçage n'est pas couvert en
bout en bout, puisque la suite part d'un compte existant. Il l'est par les tests
d'intégration de l'API et par une vérification manuelle au navigateur.
