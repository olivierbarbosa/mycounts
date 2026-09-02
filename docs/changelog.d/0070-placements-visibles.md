# Les placements reviennent sur la page Épargne, à part

**Lot** : V1-FIN-A1b | **Date** : 2026-09-02

- Régression corrigée : depuis le lot A1, un PEA ou un PER existant disparaissait de
  l'écran Épargne, qui ne lisait pas `placements` — le solde était juste, l'écran muet.
- `frontend/src/api/schema.ts` régénéré depuis l'OpenAPI (`scripts/exporter_openapi.py`
  → `openapi-typescript`), jamais édité à la main : `placements`,
  `total_placements_centimes`, `TypeCompte.placement`.
- Sous « Mes comptes », une rubrique « Placements » : chaque compte avec son solde, une
  ligne « Total placé » à part, et une phrase pour qui n'a jamais lu le modèle — cet
  argent est placé, il n'est pas compté dans l'épargne disponible. Absente quand la
  liste est vide. Chaque ligne ouvre le détail du compte, comme un livret.
- L'en-tête de `Epargne.tsx` dit ce que l'écran fait et ne fait pas (pas d'objectifs,
  pas de valeur de marché).
- `frontend/e2e/epargne.spec.ts` : un placement est dans « Placements », pas dans
  « Mes comptes », `total_centimes` ne bouge pas et `total_placements_centimes` prend
  exactement le solde d'ouverture ; le détail s'ouvre depuis la ligne.
