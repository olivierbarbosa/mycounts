# Lot C (suite) — la préparation mensuelle

Le lot C avait posé le modèle ; celui-ci le fait servir. C'est le geste du début de
période : la paie tombe, on ouvre les enveloppes, on prépare le mois.

## Elle montre avant d'écrire

Deux routes, et la séparation n'est pas une politesse : `GET /enveloppes/preparation`
calcule et **n'écrit rien**, `POST` applique les lignes qu'on lui donne. C'est la décision
d'Olivier — voir avant que ça bouge.

L'écran affiche ce qui serait libéré, ce qui serait alloué, ce qu'il resterait. Il ne
recalcule rien côté client : les montants viennent du serveur, seul auteur de la règle. Un
second calcul dans le navigateur finirait par diverger du premier.

## L'idempotence ne vient d'aucun verrou

Rejouer la préparation ne double rien, et il n'y a pourtant nulle part de marqueur
« période déjà préparée ». Le calcul part de l'état RÉEL : une enveloppe déjà servie n'a
plus la place de l'être, un reliquat déjà libéré vaut zéro. La propriété se déduit de la
formule au lieu d'être gardée par un second état à tenir d'accord avec le premier.

C'est vérifié à deux niveaux — dans le domaine, et sur le chemin complet contre PostgreSQL.

## Un reliquat en attente ne finance rien

Les enveloppes en mode « demander » proposent leur reliquat, mais il n'entre pas dans le
disponible tant que la question n'a pas de réponse. Le compter d'avance ferait promettre à
d'autres enveloppes de l'argent qu'un « non » reprendrait aussitôt.

À l'écran, le défaut est **garder** : ne rien répondre ne déplace rien.

## Ce que la ligne dit d'elle-même

`limitee_par_le_disponible` est exposé par le calcul plutôt que déduit à l'affichage :
« on vous propose 40 € » et « on vous propose 40 € parce qu'il ne restait que ça » ne
s'interprètent pas pareil, et seul le calcul sait laquelle des deux est vraie.

## Un bug pré-existant trouvé en chemin

La route `POST /enveloppes/{id}/mouvements`, livrée au lot E1, **renvoyait le solde
d'avant sa propre écriture** : allouer 200 € répondait « solde : 0 ». Les sessions du
projet sont créées avec `expire_on_commit=False`, si bien que les objets déjà chargés
gardent leur état d'avant le commit.

Aucun test ne le voyait, et la raison mérite d'être retenue : tous relisaient l'état par un
**second appel**, c'est-à-dire par le seul chemin qui contourne le cache de session. À
l'écran, l'ajustement d'une enveloppe affichait donc l'ancien montant jusqu'au
rechargement suivant.

Corrigé dans `_repartition`, qui promet « l'état actuel » et doit donc le garantir. Un test
mesure désormais la RÉPONSE elle-même, pas une relecture.

## Vérifié

40 tests unitaires sur le domaine, dont deux mutations : compter un reliquat en attente
dans le disponible fait rougir son témoin, ignorer ce qui vient d'être libéré dans le
calcul de la place fait rougir le sien. 162 tests d'intégration, 101 de bout en bout.
