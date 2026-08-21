# Basculer entre son argent et celui du foyer

Demandé par Olivier le 21 août 2026 : « switch de vue entre compte perso et foyer via un
bouton dans les paramètres, et on retrouve la même app, les mêmes écrans, mais pour le
foyer ».

## Deux mondes étanches

C'est la décision qui commande tout le reste. On répond à **« combien j'ai »** ou à
**« combien on a »**, jamais aux deux mélangés :

- **Compte personnel** : ses propres comptes privés. Les comptes joints n'y figurent pas —
  « combien j'ai » ne comprend pas la moitié du compte commun, dont la répartition
  n'appartient pas à cette application.
- **Comptes joints** : ceux du foyer, et eux seuls. Les comptes personnels n'y figurent
  pas, et c'est le sens qui PROTÈGE : les opérations personnelles de l'un ne doivent pas
  apparaître dans un écran que l'autre regarde.

Le solde, les budgets, les statistiques et les enveloppes suivent le périmètre. Un écran
qui afficherait le même total dans les deux vues signalerait que le périmètre n'a pas
suivi — c'est d'ailleurs l'un des tests.

## La vue fait partie du périmètre, pas de l'affichage

Elle vit dans le `Principal`, à côté du foyer, et non dans un paramètre de route. Une
fonction du repository qui l'oublierait rendrait des comptes qui ne sont pas les siens, et
le seul moyen d'empêcher cet oubli est qu'elle ne puisse pas être omise.

Son défaut est PERSONNELLE, et c'est un choix de sûreté : un appelant qui ne transmet rien,
ou qui transmet une valeur inconnue, voit ses propres comptes. L'inverse ferait fuiter par
simple faute de frappe dans un en-tête.

Elle voyage par l'en-tête `X-Mycounts-Vue`, posé une fois pour toutes dans le client HTTP.
Pas dans le cookie de session : elle n'est pas un secret et ne donne accès à rien de plus,
et l'y mettre obligerait à réécrire l'authentification à chaque bascule.

## Ce qui manquait pour que ce soit utilisable

- **Aucun compte joint n'était créable.** `prive: true` était écrit en dur dans l'écran des
  comptes. Une case l'ouvre, à la création seulement : basculer un compte déjà mouvementé
  changerait qui voit son historique.
- **N'importe quel membre pouvait supprimer un compte joint.** La visibilité valait
  permission, ce qui n'est vrai d'aucun objet partagé. Seule la personne qui l'a ouvert le
  supprime désormais — un 403 et non un 404, puisque le compte existe et que l'appelant le
  voit.
- **Le foyer n'avait pas de liste de membres.** Elle est là, avec qui est qui — le
  marqueur « vous » vient du serveur, deux membres pouvant porter le même nom.
- **Basculer en vue foyer sans compte joint remplaçait toute l'application** par l'écran
  d'amorçage « premier compte », paramètres compris : la bascule était un aller sans
  retour. L'amorçage ne vaut plus que pour la vue personnelle.

## Vérifié

11 tests d'intégration sur la confidentialité, dont deux mutations : laisser passer les
comptes privés en vue foyer fait rougir son témoin, et basculer le défaut sur FOYER en fait
rougir six — dont les tests de confidentialité qui existaient déjà. Deux tests d'API sur la
propriété d'un compte joint, dans les deux sens. Six tests de bout en bout sur la bascule.
