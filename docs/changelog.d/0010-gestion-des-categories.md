# Gestion des catégories à l'écran

**Lot** : 2 | **Date** : 2026-08-19

Créer, renommer, retinter, supprimer une catégorie depuis les réglages. La suppression
d'une catégorie utilisée est refusée avec une explication, et la ligne reste en place.

La **nature** (dépense / revenu) n'est modifiable nulle part : la changer inverserait le
signe attendu de toutes les opérations déjà classées dessous, et donc les totaux de mois
déjà clos. Une catégorie mal orientée se remplace, elle ne se retourne pas.

## Vérifié

4 tests de bout en bout, dont un qui vérifie qu'une catégorie créée est **proposée dans le
formulaire de saisie** — le genre de lien qu'un test d'API ne voit pas.

Témoin exécuté après redémarrage du serveur : sans la protection applicative, le test de
refus échoue. Voir ERREURS.md #017 — la première tentative testait l'ancien code, uvicorn
tournant sans rechargement automatique.
