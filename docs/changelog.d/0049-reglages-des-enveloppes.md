# Lot C — le modèle des enveloppes

Ce qui manquait au lot E1 pour que la préparation mensuelle puisse être écrite. Le point
qui commande le reste est le **rollover** : ce que devient le solde d'une enveloppe quand
une nouvelle période s'ouvre. Sans réponse à cette question, `place = max(0, cible −
actuel)` n'a pas de sens — il suppose déjà de savoir ce que vaut « actuel » au premier jour
du mois.

## Les deux décisions d'Olivier

**Trois modes**, comme le document de son collègue : `report`, `liberation`, `demander`.

**Le rollover n'écrit rien tout seul** : il sera calculé et proposé par la préparation
mensuelle, qui se valide explicitement. Cette seconde décision désamorce l'objection que
j'avais faite à la première — le mode « demander » aurait été une interruption à chaque
paie ; puisque rien ne s'écrit hors de la préparation, il devient une ligne de plus dans un
écran qu'on parcourt déjà.

Le **report est le défaut**, et c'est le seul choix qui n'appartenait pas à Olivier : c'est
le seul mode non destructif. Un défaut à `liberation` viderait les enveloppes de tous ceux
qui n'ont rien réglé, à la première préparation, sans que personne ait rien demandé.

## Ce que le domaine sait maintenant

- `UsageEnveloppe` — fonctionnement ou réserve. Une enveloppe de fonctionnement se vide
  chaque période par construction, une réserve s'accumule : les additionner dans un même
  total donnerait un chiffre qui ne veut rien dire.
- `Rollover` — les trois modes.
- `priorite` — ordre de service quand le disponible ne suffit pas. À égalité, c'est le NOM
  qui tranche, jamais l'ordre d'insertion en base : un partage d'argent qui dépend de
  l'ordre des lignes est un partage qu'on ne peut ni expliquer ni corriger.
- `contribution_mensuelle` — `None` et non zéro, pour que la préparation ne recommande RIEN
  plutôt que zéro là où l'utilisateur n'a rien fixé.

Deux fonctions pures : `reliquat_au_changement_de_periode` et `ordre_de_service`. Elles ne
décident rien, elles calculent une proposition — l'écriture appartient à la préparation.

Un cas est traité à part et vaut pour les trois modes : **un solde négatif ou nul ne libère
jamais rien**. Libérer un découvert ferait apparaître de l'argent qui n'existe pas, et
« demander » poserait une question dont les deux réponses sont identiques.

## Ce que l'écran expose

Une feuille de réglages par enveloppe, ouverte depuis l'édition — séparée de l'ajustement
du montant, qui est le geste fréquent. Chaque mode y porte **une phrase qui dit ce qu'il
fait** : « libération » ne veut rien dire pour qui n'a pas lu le modèle de données, et un
réglage qu'on ne comprend pas est un réglage qu'on laisse à sa valeur par défaut.

C'est aussi ce qui permet enfin de **renommer une enveloppe et de changer son objectif** —
l'API le permettait depuis E1, aucun écran ne l'appelait.

Règle tenue : aucune colonne n'est ajoutée sans un écran capable de la remplir. C'est
pourquoi `statut` (actif / en pause / atteint / abandonné) n'y est PAS : rien ne le
consommerait encore, et une colonne morte ment sur ce que le modèle sait. Il viendra avec
la préparation mensuelle, qui en a besoin pour cesser de servir une enveloppe close.

## Vérifié

26 tests unitaires sur le domaine, dont deux mutations : traiter « demander » comme
« libérer » fait rougir le test qui porte sur le drapeau, et retirer la garde du solde
négatif en fait rougir trois. 155 tests d'intégration, dont cinq nouveaux contre le vrai
PostgreSQL — les réglages survivent à un aller-retour, un rollover inconnu est refusé en
422, une contribution négative aussi. 98 tests de bout en bout.
