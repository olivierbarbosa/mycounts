# Lot D — Statistiques et constats

Une bulle en haut à droite, à gauche de celle du calendrier. Elle répond à « où va mon
argent » et signale ce que l'addition mentale rate.

## Toutes les catégories, et « sans catégorie » en premier s'il le faut

L'accueil montre les budgets fixés ; cet écran montre la réalité — toutes les catégories,
plafonnées ou non. « Sans catégorie » n'y est jamais masqué : c'est souvent la plus grosse
ligne, et la cacher donnerait une répartition fausse.

Pas de camembert. Au-delà de six parts les secteurs deviennent indistinguables et le foyer
en a neuf par défaut ; des barres triées par montant se comparent d'un coup d'œil. Elles
partagent la même verticale, ce qui est précisément ce qui les rend comparables.

La période PRÉCÉDENTE est lue elle aussi, et sert de point de comparaison : « 320 € de
sorties » ne dit pas si c'est beaucoup, « +18 % » si. Un poste qui n'existait pas avant est
marqué « nouveau » plutôt que « +∞ % » — les deux ne veulent pas dire la même chose, et le
second ferait passer un fait clair pour une aberration.

## Le coaching ne juge pas

**Il ne dit jamais qu'une dépense est inutile.** Personne ne peut le savoir à la place de
celui qui l'a faite : une livraison de repas peut être un caprice ou le seul dîner possible
d'une semaine chargée. Un outil de budget qui juge se trompe, et on cesse de l'ouvrir.

Ce qu'il fait à la place est plus utile et vérifiable — rendre visibles des totaux que
l'addition mentale rate. Trois motifs, tous chiffrés, tous explicables en une phrase :

- **le goutte-à-goutte** : plusieurs petites dépenses au même endroit. « Quinze commandes à
  18 € font 270 € » est un fait ; « tu commandes trop » est une opinion ;
- **un poste en hausse franche** par rapport à la période précédente ;
- **le coût ANNUEL des abonnements**, que les douzièmes rendent invisible — trois euros par
  mois ne se lisent jamais comme trente-six.

**Aucune marque n'est nommée.** Une liste de commerçants en dur serait fausse dès qu'on
change de pays ou d'habitudes. Le regroupement se fait sur le libellé tel qu'Olivier
l'écrit, normalisé — accents, casse et ponctuation retirés — ce qui attrape ses propres
habitudes sans qu'on ait à les deviner. « Uber Eats », « UBER EATS » et « uber-eats » sont
le même endroit ; « Carrefour » et « Carrefour City » restent deux, parce qu'un
rapprochement approximatif ferait des regroupements qu'on ne pourrait pas défaire.

**Aucun modèle de langage**, et le garde-fou nº 3 y veille. Rien ici n'en aurait besoin :
ce sont des sommes, des tris et des seuils.

## Les seuils sont nommés et bornés des deux côtés

Trois occurrences et 50 € pour le goutte-à-goutte ; +30 % sur au moins 30 € pour une
hausse. Ils sont écrits en tête de module plutôt que dissimulés dans une condition — c'est
le genre de valeur qu'on veut relire et discuter. Chacun a son test juste en dessous et
juste au-dessus : un seuil qu'on ne franchit jamais dans les deux sens est un seuil qu'on
n'a pas vérifié.

## Un bug attrapé par le typage

Une première version du filtre lisait les drapeaux d'opération par `getattr(..., défaut)`.
Elle compilait, passait mypy, et rendait `False` pour un `est_virement` qui **n'existe
pas** — la colonne s'appelle `virement_id`. Tous les virements seraient entrés dans les
statistiques comme des dépenses, gonflant le total à chaque mise de côté. Un accès
dynamique à un attribut qu'on croit connaître est un typage qu'on s'est retiré à soi-même.

## Vérifié

26 tests unitaires sur le domaine, dont deux mutations : transformer la hausse en écart
absolu fait rougir le témoin qui interdit d'alerter sur une BAISSE, et abaisser le seuil du
goutte-à-goutte fait rougir celui qui le borne par en dessous. 168 tests d'intégration,
105 de bout en bout.
