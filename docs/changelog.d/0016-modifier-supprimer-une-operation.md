# Modifier et retirer une opération

**Date** : 2026-08-19

Saisir une dépense était jusqu'ici **à sens unique** : aucun écran ni aucune route ne
permettait de la corriger ou de la retirer. C'est pourtant l'action la plus fréquente de
l'application.

## Deux retraits différents, une seule demande

- Une **saisie manuelle** est supprimée pour de bon.
- Une opération **issue d'un prélèvement** est marquée annulée et **conservée**.

La conserver n'est pas un détail : sa suppression paraîtrait juste jusqu'au passage
suivant du job, qui la recréerait — sa clé d'idempotence
(`uq_operation_par_echeance`) ne la verrait plus. La ligne annulée est précisément ce qui
rend le retrait définitif.

L'appelant demande simplement le retrait ; le repository choisit selon `recurrence_id`.

## Quatrième dimension de la table d'agrégats

`COMPTE_LES_ANNULEES` rejoint `CONTRIBUTIONS`, `SIGNE_RETENU` et `INCLUT_OUVERTURES` :
exhaustive, testée, sans branche par défaut. Elle ne varie pour l'instant selon aucun
agrégat — une opération annulée n'entre nulle part — mais elle est écrite comme une table
pour que le jour où un journal d'audit voudrait les compter, il faille le **déclarer** au
lieu de l'oublier.

## Ce qui n'est pas modifiable, et pourquoi

- Le **compte** : déplacer une opération changerait le solde de deux comptes.
- **`est_paie`** : basculer une opération en paie déplacerait les bornes de toutes les
  périodes suivantes, donc des totaux déjà consultés.

Ces deux corrections passent par une suppression et une nouvelle saisie, où elles se
voient.

## Vérifié

9 tests d'intégration. Deux témoins exécutés contre leur implémentation fautive :
remplacer l'annulation par une suppression sèche fait rougir 2 tests, et retirer
l'exclusion des annulées de la table d'agrégats en fait rougir 1.
