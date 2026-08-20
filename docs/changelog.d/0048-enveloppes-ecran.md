# Lot B — l'écran des enveloppes

Même traitement que l'écran des budgets, plus le trou de couverture que le lot E1 avait
laissé derrière lui.

## Des lignes, pas des cartes

Chaque enveloppe occupait une plaque de verre de 16 px de marge intérieure portant cinq
lignes — nom, montant, barre, détails, et un bouton « Supprimer » toujours visible. Trois
enveloppes remplissaient l'écran.

Il reste une ligne : nom, montant sur objectif, crayon. Puis la barre. L'état ne prend une
ligne que lorsqu'il a quelque chose à dire.

## Ajuster, et non supprimer-recréer

Le crayon ouvre un champ pré-rempli au montant réservé. On y saisit le montant **visé**,
pas un écart : c'est le chiffre qu'on a sous les yeux, et exiger de calculer soi-même
« je veux 50 € de plus » à partir de « il y en a 200 » ajoute une soustraction mentale à
chaque ajustement. Même parti pris que la correction du solde réel.

L'écart devient un mouvement dont le TYPE porte le sens — allocation vers le haut, reprise
vers le bas — jamais le signe. Viser ce qui est déjà réservé n'écrit rien : un mouvement de
zéro salirait le journal sans rien dire.

Le retrait a rejoint l'édition. C'est l'action la plus rare et la seule irréversible.

## La création ne demande qu'un nom et une somme

Catégorie et objectif se replient : ils se remplissent une fois sur trois et allongeaient
le formulaire de deux lignes à chaque création. Le sélecteur de catégorie est celui de la
saisie — donc on peut y créer une catégorie manquante sans quitter l'écran.

## L'écran n'avait aucun test de bout en bout

Le lot E1 l'avait livré sans témoin. Six désormais, dont le seul qui compte vraiment :
**réserver ne déplace aucun argent**. Il mesure deux grandeurs qui bougent en sens opposés
— le réservé monte, le non-affecté baisse — pendant qu'une troisième ne bouge pas du tout :
le solde réel des comptes. C'est la règle qui commande tout le module, et la seule dont une
violation ne se verrait pas tout de suite.

Deux défauts de méthode corrigés en écrivant ces tests, tous deux du genre « le test ne
mesure pas ce qu'il croit » :

- ils passaient seuls et échouaient en groupe, parce qu'ils lisaient l'API dans la foulée
  du clic sans attendre que l'écriture soit acquittée. Une course, pas un défaut du code ;
- le helper `connecter` de `parcours-saisie.spec.ts` rendait la main pendant que la requête
  de connexion était encore en vol. Les tests qui enchaînaient sur un élément d'interface
  s'en tiraient ; tout appel direct à `page.request` recevait un 401 silencieux.

## La coche « c'est ma paie » a disparu

Signalé par Olivier : elle subsistait en Revenu **et** en Virement. Sa condition était
`!sortie`, vraie pour les deux — une négation qui décrivait deux cas là où elle en visait
un. Une paie est un revenu de catégorie Salaire, rien d'autre.

Le témoin de cette règle a lui-même dû être refait : la première version vérifiait la
mention affichée à l'écran, et restait verte quand on remplaçait l'envoi par
`est_paie: false`. Il mesure désormais ce qui part au serveur, et son pendant vérifie
qu'un revenu d'une autre catégorie n'est PAS une paie.
