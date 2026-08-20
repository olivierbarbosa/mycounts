# Enveloppes — le noyau (lot E1)

Une enveloppe est une **part réservée de l'épargne**, rattachée à une catégorie de dépense.
Elle répond à « combien ai-je de disponible, et pour quoi ».

## La règle qui commande tout le module

> Une allocation vers une enveloppe ne crée **jamais** de mouvement bancaire.

Le compte dit où l'argent **est**, l'enveloppe à quoi il est **promis**, le budget ce qu'on
prévoit d'y mettre. Réserver 200 € pour les vacances ne déplace pas 200 € : cela dit que
200 € des livrets sont promis aux vacances. L'argent était déjà là.

Le témoin le vérifie sur **trois grandeurs** : l'épargne totale ne bouge pas, le réservé
monte, et le nombre d'opérations en base reste identique. Sans la troisième, une allocation
qui écrirait discrètement une opération passerait — vérifié par mutation, six tests
rougissent.

## Aucun solde n'est stocké

Il se recalcule depuis un **journal de mouvements**, comme le solde d'un compte se
recalcule depuis ses opérations. Corriger une enveloppe consiste à ajouter un mouvement,
jamais à réécrire une valeur : six mois plus tard, c'est la seule façon de comprendre un
écart.

Tous les montants sont **positifs** ; c'est le type qui dit le sens. Un montant signé
rendrait possible une allocation négative — une reprise déguisée, invisible dans un journal
filtré par type. Un test balaie le produit cartésien des types deux à deux : un type ajouté
sans qu'on décide de son sens fait rougir la suite au lieu de compter en silence du mauvais
côté.

## Trois règles de calcul qui se voient à l'écran

- **Une enveloppe peut passer en négatif.** Une dépense réelle ne se bloque pas parce que
  l'enveloppe est mal financée.
- **Le réservé ne compte que les soldes positifs.** Une enveloppe dans le rouge ne rogne
  pas ce que les autres promettent : si les vacances sont à −50, cela n'enlève rien aux
  900 € d'impôts.
- **Le non-affecté peut être négatif.** Le borner à zéro cacherait exactement ce qu'il faut
  voir : que les promesses ne sont plus couvertes par ce qui est en banque.

Les enveloppes découpent l'**épargne** et non le compte courant : les rapporter au
quotidien ferait croire qu'on peut réserver ce qui sert à vivre le mois. Le témoin ajoute
un compte courant bien garni et vérifie que rien ne change.
