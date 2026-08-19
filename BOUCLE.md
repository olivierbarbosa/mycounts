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

> Attention il faut une version pc aussi

> Pour l'UI je veux ce design d'UI néon et Liquid Glass

*(accompagné de deux captures de l'application Revolut. Elles ne sont PAS versionnées :
l'une contenait un IBAN réel, un solde et des libellés d'opérations. Seules les
caractéristiques de direction artistique en ont été tirées.)*

> Il faut mettre des catégories par défaut et on peut ajouter ou modifier des catégories
> voir les supprimer

> Pour le premier lancement on peut demander à l'utilisateur de taper son solde actuel

> Sur le design ajout un effet glow néon et un halo sur le background avec du dégradé

> La couleur du background est trop prenonce je pense

> https://webgradients.com/palette/revolut-website-color-palette utilise cette palette de
> couleur
>
> ou celle la plutot : https://webgradients.com/palette/stripe-website-color-palette

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
| « il faut une version pc aussi » | Mobile-first **reste la base**, mais le bureau doit avoir sa propre mise en page, pas un mobile étiré. À partir de 1024 px : navigation en **rail latéral** (plus de tab bar basse), contenu élargi. Le garde-fou n°10 vérifie qu'à 1280 px la navigation n'est plus en bas de l'écran. |
| « design d'UI néon et Liquid Glass » | **Révise la DA du lot 1.** Fond en dégradé violet profond au lieu d'un aplat quasi noir, accents néon (cyan/magenta), verre laiteux étendu aux cartes de contenu, montants en display XL avec centimes réduits, boutons d'action circulaires, tab bar très translucide. Contrepartie non négociable : tout texte posé sur verre ou dégradé passe un contrôle de contraste AA automatique — voir la décision D3. |
| « catégories par défaut + ajouter / modifier / supprimer » | **Annule et remplace la réponse au QCM D1.** La liste par défaut est rétablie, et l'API gagne modification et suppression. Une catégorie déjà utilisée ne peut pas être supprimée (contrainte `RESTRICT`) : elle s'archive, sinon les totaux d'un mois clos changeraient rétroactivement. |
| « au premier lancement, demander son solde actuel » | Modélisé en **opération d'ouverture**, pas en colonne `solde_initial`. Un solde reste une somme d'opérations — le stocker créerait la seconde source de vérité que tout le projet évite. L'opération porte `est_ouverture` pour être exclue des dépenses : un découvert de départ n'est pas une dépense du mois. |
| « effet glow néon et halo sur le background avec dégradé » | Deux halos radiaux fixes sur le fond (violet en haut, cyan en bas), plus une lueur néon sur les surfaces en verre et les éléments actifs. **Les halos passent DERRIÈRE le contenu et ne portent jamais de texte** : le contrôle de contraste AA reste la limite, et il a déjà refusé deux versions de la pastille de catégorie. |
| « le background est trop prononcé » | Dégradé et halos **désaturés d'un cran** : le violet passe de `#5B21B6` à `#3B1D73` en haut, et les halos perdent environ la moitié de leur opacité. Le glow reste sur les surfaces et les éléments actifs, où il est voulu ; c'est le fond qui redevient un fond. |
| « utilise la palette Stripe » | Palette reprise telle quelle : `#635bff` primaire, `#0a2540` fond sombre, `#f6f9fc` surface claire, `#00d4ff` accent. Le fond passe du violet au **bleu nuit**. Contrainte inchangée : le contraste AA arbitre — `#635bff` sur blanc donne 4,68:1, il passe de justesse et devient donc la limite basse ; `#00d4ff` ne portera jamais de texte, il reste aux lueurs et aux liserés. |
| « surtout prévu pour mobile & tablette » | Mobile-first strict : `min-width` uniquement, tab bar basse, safe areas, cibles ≥ 44 px. |

## État du chantier

- **Lot 0 — socle** : en cours.
- Lots 1 à 5 : voir le plan.

## Décisions prises par défaut, à confirmer

**Depuis le 2026-08-19, chaque décision est posée en choix multiples** plutôt que
consignée ici en silence — demande explicite. Ce tableau garde la trace de ce qui a été
tranché, et de ce qui reste ouvert.

| # | Question | Option retenue | Coût si tu choisis l'autre | Fichier à changer |
|---|---|---|---|---|
| ~~D1~~ | ~~Liste de catégories~~ | **TRANCHÉ le 2026-08-19** : aucune catégorie imposée. L'utilisateur crée les siennes et peut en ajouter à tout moment, y compris depuis l'écran de saisie. L'amorçage automatique a été supprimé. | — | fait |
| ~~D2~~ | ~~Ancrage du premier cycle~~ | **CONFIRMÉ le 2026-08-19** : la première paie saisie ouvre le cycle. | — | fait |
| ~~D4~~ | ~~Période sans paie~~ | **CONFIRMÉ le 2026-08-19** : mois civil marqué « estimé ». | — | fait |
| ~~D5~~ | ~~Niveau du réglage `paies_par_cycle`~~ | **CONFIRMÉ le 2026-08-19** : par personne. À revoir au lot 5 pour les plafonds partagés. | — | fait |
| D6 | Comment stocker la couleur d'une catégorie ? | **Une teinte nommée** (violet, cyan, vert, ambre, rose, ardoise), résolue par `tokens.ts`. | Stocker un code hexadécimal = contourner le garde-fou n°9, et rendre impossible l'adaptation clair/sombre. | `backend/mycounts/models/budget.py` |
| D3 | Les montants peuvent-ils être posés sur du verre, maintenant que la DA néon l'étend aux cartes ? | **Oui, mais sous condition mesurée** : tout texte sur verre ou dégradé doit passer un contraste AA (4,5:1), vérifié automatiquement dans les trois positions du réglage de transparence. La règle « jamais de montant sur du verre » du lot 1 est donc remplacée, pas abandonnée. | Revenir à des cartes opaques = plus sûr en lisibilité, mais on perd l'essentiel de l'effet demandé. | `frontend/src/design/tokens.ts`, `frontend/e2e/contraste.spec.ts` |

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
