# Écran Budget et jauges sur l'accueil

Le backend des plafonds était livré et testé depuis le lot 4 ; **aucun écran ne l'exposait**.

- Les jauges apparaissent sur l'**accueil**, avant la liste des opérations : ce qu'on vient
  vérifier en ouvrant l'application, c'est « est-ce que ça tient », pas « qu'ai-je acheté ».
- « Gérer » ouvre l'écran **Budgets**, poussé depuis la droite comme les paramètres, où
  l'on fixe et retire les plafonds.

Une barre et non un camembert : un ratio unique contre une limite est le cas de la jauge,
et au-delà de six parts les secteurs deviennent indistinguables — le foyer en a neuf par
défaut. Consommé et à-venir sont **deux segments séparés de 2 px**, jamais fondus. L'état
n'est jamais porté par la seule couleur : un dépassement s'écrit en toutes lettres.

## L'alerte ne pouvait pas se déclencher

`a_venir` ne comptait que les opérations à l'état `prevue`, et **rien n'en crée** : le
futur n'est dans aucune table, c'est une projection. `depasse_avec_les_echeances` — décrit
dans le plan comme « le vrai signal » — n'était donc qu'un synonyme de `depasse`.

La projection des échéances vit désormais dans le dépôt, partagée par l'agenda et les
plafonds. Témoin d'intégration qui part d'une récurrence, comme l'utilisateur.

## Deux détails corrigés en chemin

- `<Montant>` affichait « +100,00 € » pour une limite : un plafond n'est pas un crédit.
- Un lien « Gérer » en `accent-clair` mesurait 4,00:1 en thème clair. Cette teinte n'avait
  jamais servi qu'à des bordures — convention désormais écrite dans `tokens.ts`.
