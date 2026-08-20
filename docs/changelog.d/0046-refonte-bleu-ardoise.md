# Refonte visuelle : bleu ardoise, navbar Apple Music, écrans allégés

Demandée par Olivier le 20 août 2026, en plusieurs vagues consignées mot pour mot dans
`BOUCLE.md`.

## Palette

La direction artistique passe du lavande au **bleu ardoise** : `#334155`, `#0EA5E9`,
`#7DD3FC`, `#E0F2FE`, `#F1F5F9`. Le thème sombre en est dérivé plutôt que d'être une
seconde identité — l'ardoise y devient le fond en descendant à `#0F172A`.

La répartition des rôles n'est pas esthétique mais **mesurée** : `#0EA5E9` avec du texte
blanc ne donne que 2,77:1 là où AA en demande 4,5. Il ne porte donc aucun texte. En thème
clair il tombe à 2,53:1 même comme aplat graphique — sous le seuil de 3:1 des composants
non textuels — et s'y assombrit en `#0284C7`, puis en `#0369A1` dès qu'il porte du texte.
Les boutons pleins ne montent jamais plus clair que `#0369A1` (5,93:1 avec du blanc).

Le rouge des débits `#FB7185` est conservé sur décision explicite d'Olivier, avec une
dérogation bornée à 3,5 dans `e2e/contraste.spec.ts`. Voir ERREURS.md #035 : le chiffre de
6,63:1 que j'avais d'abord annoncé était mesuré sur un aplat, pas sur le rendu.

## Navigation

La barre d'onglets adopte le modèle d'Apple Music : **deux capsules de verre distinctes**,
les onglets dans une pilule, l'ajout seul dans un disque à sa droite. Le `+` occupait
auparavant un emplacement d'onglet au milieu de la pilule, ce qui le faisait lire comme une
destination et obligeait la pastille glissante à sauter par-dessus son index.

Le Liquid Glass y est déclaré en quatre couches — reflet spéculaire, teinte, deux liserés
internes qui donnent l'épaisseur, ombre portée.

## Les bulles du haut

`BulleAvatar` et `BulleAction` étaient deux composants jumeaux aux feuilles de style
recopiées. Ils fusionnent en un seul `Bulle`, et surtout **tous les écrans qu'elles ouvrent
partagent désormais la même mécanique** (`useEcranDeBulle`) : éclosion depuis le point
touché, repli vers lui, et **glissement de retour au doigt** depuis le bord gauche — que
WebKit ne fournit pas en PWA `standalone`.

Le calendrier monte désormais sa coquille SANS attendre le réseau : il renvoyait `null`
jusqu'à ce que quatre appels enchaînés aient répondu, si bien que toucher la bulle ne
produisait rien du tout pendant ce temps. Deux de ces appels partent maintenant en
parallèle.

## Écrans allégés

- **Accueil** : un seul chiffre en grand, trois mesures secondaires sur une ligne de
  colonnes égales, les jauges en lignes plates plutôt qu'en cartes de verre, le journal
  groupé par jour. Le solde d'ouverture quitte la liste — c'est une ligne d'amorçage, pas
  une dépense. « Corriger » devient un crayon.
- **Budget** : une ligne par plafond au lieu d'une carte de six lignes, édition en place
  par un crayon, retrait déplacé DANS l'édition, formulaire d'ajout déplié à la demande
  **à la place du bouton**, en bas — ouvert en haut, il renvoyait le regard à l'opposé du
  doigt.
- **Modales** : elles se ferment par un appui en dehors.

## Catégories

Une catégorie manquante se crée **sur place**, dans le sélecteur de la saisie comme dans
celui des budgets (`ChoixCategorie`) : c'est en saisissant une dépense qu'on découvre
qu'elle manque. La teinte est attribuée automatiquement, la moins employée d'abord.

« Remboursement » rejoint les catégories initiales — pour les foyers NEUFS seulement.

La case « c'est ma paie » disparaît quand la catégorie choisie est « Salaire ». Côté
serveur, `est_paie` reste une colonne explicite : déduire la règle d'un nom la rendrait
invisible et cassable par un renommage.

## Échelle de plans

`tokens.ts` porte désormais l'ordre d'empilement complet, nommé par rôle. Il naît d'un
défaut signalé par Olivier : une feuille modale ouverte depuis le calendrier s'affichait
DERRIÈRE lui. Voir ERREURS.md #038.

## Outillage

`make front-lint` ne vérifiait rien depuis le début du projet — voir ERREURS.md #034.
