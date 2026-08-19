# Frontend : connexion, shell mobile-first et version bureau (lot 1)

**Lot** : 1 | **Date** : 2026-08-19

## Ajouté

- Vite + React + TypeScript. Types de l'API **générés** depuis l'OpenAPI
  (`scripts/exporter_openapi.py` → `openapi-typescript`), jamais écrits à la main.
- `design/tokens.ts` — auteur unique des couleurs, rayons, espacements et graisses, en
  thème clair et sombre. Les composants n'écrivent que `var(--…)`.
- Liquid Glass (recette iOS 27 : flou, saturation, bord assombri, reflet spéculaire),
  **réservé aux couches flottantes**. Aucun montant n'est posé sur du verre.
- Réglage de transparence à trois positions, plus `prefers-reduced-transparency` et
  `prefers-reduced-motion` respectés : l'app reste utilisable verre désactivé.
- Écran de connexion branché sur l'API, écran d'accueil, invitation d'un membre.
- **Version bureau** : à partir de 1024 px, la navigation devient un rail latéral et le
  contenu passe en deux colonnes. Une tab bar basse sur écran large est un mobile étiré.

## Garde-fous ajoutés

- **n°9** — aucune couleur ni rayon en dur hors de `tokens.ts`. Les commentaires sont
  retirés avant analyse : « ERREURS.md #008 » ressemblait à une couleur hexadécimale.
- **n°10** — Playwright sur 390 / 820 / 1280 px : aucun débordement horizontal, cibles
  tactiles ≥ 44 px, champs ≥ 16 px (en dessous, iOS Safari zoome), et la navigation doit
  tenir entièrement dans la fenêtre.

## Vérifié

12 tests de bout en bout dans un navigateur réel, plus un parcours manuel complet
(mauvais mot de passe refusé, puis connexion, puis invitation). Playwright démarre
lui-même uvicorn et Vite : aucun processus lancé à la main.

Trois erreurs consignées, chacune trouvée par une mesure et non par l'œil :
ERREURS.md #007 (je vérifiais l'application d'un autre projet), #008 (la barre dépassait
de 41 px sous la fenêtre, invisible sur une capture), #009 (le script créait des comptes
que l'API refusait ensuite).
