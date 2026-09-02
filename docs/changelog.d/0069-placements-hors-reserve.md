# Les placements sortent de la réserve d'épargne

**Lot** : V1-FIN-A1 | **Date** : 2026-09-02

- Troisième nature de compte, `placement` (`domain/comptes.py`) : PEA, PEA-PME, PEE
  (nouveau produit), compte-titres, assurance vie et PER. Ni quotidien, ni réserve : le
  résumé de l'accueil les ignore, les enveloppes ne les découpent pas. Le LEP reste une
  épargne disponible, comme tous les livrets.
- Le solde par compte ne change pas : un placement garde ses opérations, son solde et son
  détail. `GET /epargne` le rend à part, dans `placements` et `total_placements_centimes`,
  jamais additionné à `total_centimes`.
- Migration `7b3e9c2a5d41` : reclassement EXPLICITE par clé de produit, figé dans la
  migration ; retour arrière mesuré sur de vraies lignes. Contrainte
  `ck_compte_type_connu`, dérivée de l'énumération dans le modèle.
- Un produit « Autre — placé » par symétrie avec les deux « Autre » existants.
- Non livré ici : l'écran (le front compile, `schema.ts` sera régénéré avec l'écran) ;
  la valeur de marché des placements reste hors V1.
