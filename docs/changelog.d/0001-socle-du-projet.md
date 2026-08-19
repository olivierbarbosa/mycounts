# Socle du projet (lot 0)

**Lot** : 0 | **Date** : 2026-08-19

Pose l'outillage et les primitives de domaine. Aucune table métier, aucun écran.

## Ajouté

- `CLAUDE.md`, `ERREURS.md`, `BOUCLE.md`, `docs/changelog.d/`.
- `backend/mycounts/domain/montants.py` — type `Cents`, `parse_montant()` sans flottant.
- `backend/mycounts/domain/calendrier.py` — `aujourd_hui()`, `bornes_du_mois()` (mois civil).
- Squelette FastAPI (`/health`), base SQLAlchemy, Alembic, `docker-compose` PostgreSQL 16.
- Six garde-fous dans `scripts/`, tous prouvés par un témoin dans `tests/unit/test_garde_fous.py`.
- `Makefile` (auteur unique des contrôles) et CI GitHub Actions qui l'appelle.

## Vérifié

- 65 tests unitaires, 7 tests d'intégration contre un PostgreSQL réel.
- Chaque garde-fou a été exécuté contre la faute qu'il prétend détecter **et** contre le
  cas voisin légitime, pour qu'il ne se contente pas de crier sur tout.
- Deux témoins écrits d'abord se sont révélés décoratifs, mesure à l'appui (ERREURS.md
  #002 et #003) ; ils ont été remplacés par des contrôles qui échouent réellement.

## Décisions notables

- Port PostgreSQL **5434** : le 5433 est occupé par un autre projet local.
- Garde-fou « une seule tête Alembic » formulé en « **au plus** une tête » : zéro migration
  existe au lot 0, et « exactement une » aurait été rouge dès le premier jour.
- Aucun fichier n'est exempté du garde-fou secrets, pas même son propre test : les valeurs
  de test y sont assemblées à l'exécution. Une exemption serait le trou par lequel un vrai
  secret passerait.
