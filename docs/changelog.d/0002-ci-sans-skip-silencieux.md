# La CI ne peut plus être verte sans avoir exécuté les tests d'intégration

**Lot** : 0 | **Date** : 2026-08-19

Le fixture des tests d'intégration appelait `pytest.skip()` quand PostgreSQL est
injoignable. En CI, une base indisponible aurait donc produit un job **vert** avec zéro
test exécuté sur le chemin de production.

Désormais : `skip` hors CI (le poste local n'a pas toujours Docker démarré), `fail` sous
`CI=1`. Les deux branches ont été exécutées pour le vérifier — 7 skipped en local,
7 errors sous `CI=true`.

Voir ERREURS.md #004.
