# API budget : comptes, catégories, opérations, résumé de période

**Lot** : 2 | **Date** : 2026-08-19

`domain/resume.py` assemble « période + opérations → chiffres affichés ». Auteur unique :
si chaque écran refaisait ce calcul, le mobile et le bureau finiraient par afficher deux
soldes différents pour la même journée.

Routes : `/comptes`, `/categories`, `/operations`, `/resume`. Le foyer naît désormais avec
ses catégories par défaut (décision D1).

## Deux points de sécurité

- Un compte appartenant à un autre foyer renvoie **exactement** la même réponse qu'un
  identifiant inexistant — corps compris. La distinction révélerait son existence, et le
  test compare les deux réponses.
- Les montants circulent en **centimes entiers**. Un `12.50` en JSON redeviendrait un
  flottant côté client : l'invariant du projet s'arrêterait à la frontière HTTP.

## Vérifié

9 tests d'intégration sur l'API, dont la borne de période : une opération antérieure à la
paie appartient au cycle précédent et n'apparaît pas dans la liste courante, tout en
restant accessible via `?periode_courante=false`.
