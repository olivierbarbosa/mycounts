# Les corrections de solde se relisent

- `GET /api/comptes/{id}/ajustements` rend les corrections d'un compte, la plus récente
  d'abord ; l'ordre appartient au repository, qui départage par `cree_le` deux corrections
  du même jour.
- La feuille de correction les affiche sous le formulaire, à côté du geste qui les produit.
- Elles restent absentes du journal de l'accueil : un ajustement n'est pas un achat.
