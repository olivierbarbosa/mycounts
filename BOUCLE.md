# BOUCLE — état du chantier et remarques brutes

## Remarques brutes

Recopiées **mot pour mot**, sans correction ni reformulation. La formulation d'origine
contient souvent l'information qu'une reformulation perd.

### 2026-08-19 — cadrage initial

> On va juste faire une appliction de gestion de budget et de quoi rentrer chaque dépense
> et chaque salaire + planning de prélèvement ou l'on verra les prochains prélèvement a
> quelle date avec un agenda accessible rapidement c'est juste pour suivre ces dépenses et
> mieux épargner et dépenser moins dans des choses inutiles

> On va d'abord faire la version local pour faire toutes l'app une fois fonctionnel je la
> balancerais sur mon vps de prod donc il faut également que l'on prévois la sécurité
> autour de tout ça.

> Tous

*(en réponse à « quel écran doit marcher de bout en bout en premier ? »)*

> Python/FastAPI + PostgreSQL + React pour l'app web + React Expo ou Flutter pour l'app
> iOS / Android

> Par ailleurs l'identité visuel j'aimerais me rapprocher d'une app a la révolut sur la DA
> et les couleurs

> avec du liquid glass et être dans ce qu'utilise actuellement iOS 27 comem direction
> artistique

> J'oubliais mais l'app web devra toujours être surtout prévu pour mobile & tablette

> Ah oui j'oubliais mais tu peux aussi compter que le mois commence quand la personne a
> saisie sa paie donc 1 mois egale de paie a paie

> Les paies sont toujours sur le compte privé et commençons d'abord par le compte privé
> puis on fera ensuite les comptes joint

> Fin quand une nouvelle paie est rentré mais on peut calculer approximativement

> Non on peut set le nombre de fois où on est payé dans 1 mois et tu peux commit ça je te
> laisse gérer en automatique

## Traduction en décisions

| Remarque | Ce qui en a été tiré |
|---|---|
| « juste rentrer chaque dépense et chaque salaire » | Saisie manuelle seule. Aucun import de fichier ni agrégateur bancaire en V1. |
| « planning de prélèvement […] agenda accessible rapidement » | Récurrences + agenda. « Accessible rapidement » → l'agenda est une destination de la tab bar, pas un sous-écran. |
| « mieux épargner et dépenser moins dans des choses inutiles » | C'est le critère de réussite du produit. Un écran qui n'aide pas à ça ne mérite pas d'exister. |
| « d'abord la version local […] puis mon vps » | Architecture serveur dès le départ, pas local-first. Le durcissement se conçoit maintenant. |
| « Tous » | Lu comme le périmètre V1, pas l'ordre de livraison. Séquencé en lots — arbitrage assumé, à contester si c'est un contresens. |
| « 1 mois egale de paie a paie » | **Contredit le mois civil.** `bornes_du_mois()` (mois calendaire) reste une primitive de bas niveau ; une notion distincte de *période budgétaire* est nécessaire. Trois points restent à trancher — voir Points ouverts. |
| « commençons d'abord par le compte privé puis les comptes joint » | **Réordonne les lots** : compte privé et période personnelle d'abord, foyer partagé et comptes joints ensuite. Fait tomber l'objection sur les plafonds partagés : chaque personne a sa propre période, définie par sa paie. `foyer_id` reste présent en base dès le début pour éviter une migration transverse plus tard. |
| « Fin quand une nouvelle paie est rentré mais on peut calculer approximativement » | La période se clôt à la paie suivante ; tant qu'elle n'est pas saisie, la fin est **estimée** (paie précédente + 1 mois) et l'écran l'étiquette comme telle. |
| « la date de la paie fait foi » | La période s'ouvre à la `date_operation` de la paie, jamais au jour de saisie. Le résultat ne dépend pas de la ponctualité de l'utilisateur. |
| « on peut set le nombre de fois où on est payé dans 1 mois » | Réglage `paies_par_cycle` (1, 2, 4…). La période s'ouvre à la **première** paie du cycle ; les suivantes sont des revenus à l'intérieur et ne rouvrent pas de période. Les plafonds restent donc par cycle. Interprétation à confirmer : l'autre lecture (chaque paie ouvre une période) donnerait 2 périodes par mois. |
| « surtout prévu pour mobile & tablette » | Mobile-first strict : `min-width` uniquement, tab bar basse, safe areas, cibles ≥ 44 px. |

## État du chantier

- **Lot 0 — socle** : en cours.
- Lots 1 à 5 : voir le plan.

## Points ouverts

- **Période budgétaire quand les comptes joints arriveront** : les plafonds du foyer
  auront besoin d'une période commune, alors que chaque membre aura la sienne (sa paie).
  À trancher au lot du partage, pas avant.
- **Ancrage du premier cycle** : quand `paies_par_cycle` > 1, quelle paie ouvre le tout
  premier cycle ? Ensuite la règle se déduit (celle qui suit la fin du cycle précédent),
  mais l'amorçage demande un choix de l'utilisateur — à traiter au lot 2.

- Expo vs Flutter — tranché après le lot 4.
- Liste de catégories par défaut ou libre — au lot 2.
- Sort des opérations sans catégorie vis-à-vis des plafonds — au lot 4.
