# Virements entre comptes et page Épargne

Un virement n'est ni une dépense ni un revenu : l'argent change de poche sans quitter le
foyer. C'est la **cinquième dimension** de `domain/agregats.py` — il reste dans les soldes
des deux comptes et sort des dépenses de période, sans quoi mettre 200 € de côté ferait
sauter tous les plafonds du mois.

- Troisième option « Virement » dans la feuille de saisie, avec source, destination et
  inversion du sens en un geste. Le montant est unique et positif : le sens est porté par
  le couple de comptes, jamais par un signe.
- Les comptes ont un **type**, courant ou épargne, choisi à la création et non modifiable.
- Le solde de l'accueil ne porte plus que sur les comptes **courants** : mélanger un livret
  au compte courant fait croire à une aisance qui n'existe pas.
- Page **Épargne** : total, solde de chaque livret, et versé sur la période — seulement les
  virements entrants, parce que cette ligne mesure un effort et non un solde.
- Section **Comptes bancaires** dans les Réglages, sans laquelle la page Épargne renvoyait
  vers un écran qui n'existait pas.

Pas d'objectifs chiffrés : ils n'ont de sens qu'une fois les comptes alimentés, et réserver
une part d'un compte à un projet serait un second système comptable à tenir d'accord avec
le premier.

Le témoin, joué à l'écran : après un virement, le solde du quotidien baisse, l'épargne
monte, et « dépensé sur la période » **ne bouge pas**.
