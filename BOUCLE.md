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

> c'est bug les catégories & moi je voulais pour l'agenda un vrai calendrier ou l'on vois
> les logos des abonnements avec un UI beau et un format simple savoir si c'était tous les
> mois ou par an le prélèvement

> Tu peux aussi retravailler la navbar je la trouve immonde
>
> enfaite l'idée de la navbar était bien l'effet qui était mal fait dessus et la couleur je
> pense ça faisait pas assez prenium

> Pars sur quelque chose de moins bleu pour la navbar qui ce fond mieux avec le background
> de la page et pour les boutons il faudrait ajouter un contour + dégradé

> essaye cette palette de couleur : #FFF4BF #FFBEFB #DC95FF #8C56D4

> Agenda tu peux renommer en Calendrier et on peut y ajouter que les prélèvements aucun
> revenu. Le but de cette page est seulement de :
> * Ajouter un prélévement pour calculer ses charges
> * Savoir en un coup d'oeil quand et qui prélève a quelle date
> * Ajouter un prélèvement ou charge mensuellement ou anuellement si il débit 1x par mois
>   ou alors 1x par an ou même trimestrielle il faut prendre en compte un peu tout les
>   types de prélèvement

> Attention par contre quand tu travaille l'UI & l'UX il faut surtout penser simple et
> efficace on veut aller au plus rapide et surtout penser aux utilisateurs smartphone qui
> on un ecran pas aussi grand qu'une tablette et pc

> Attention il faut pouvoir supprimer un prélèvement également

> et il faut afficher le calendrier aussi sur les versions tablette et téléphone

> Pour les icones des pages je te laisse aller chercher une vrai blibliothèque pour un
> rendu prenium

> Et il faudrait implémenter quand on a pas le logo qu'on puisse par rapport a un nom que
> ça recherche le logo sur internet et l'importe depuis le site officiel

> Je reviens sur ce que j'ai dis il faut pouvoir : Modifier/Ajouter/Supprimer un
> prélèvement.

> Et le a venir c'est toujours sur le mois en cours on veut voir les prélèvement qui ne
> sont pas encore passé sur le mois en cours

> Pareil il faut ajouter le fait de pouvoir supprimer modifier une dépense

> et regarder le détails aussi

### 2026-08-20 — corrections, direction artistique, épargne et mouvement

> ça me mets not found au moment de vouloir supprimer

> ajoute une texture sur le background de fond stp

> fait que le halo ce déplace aussi sur la page entière

> Il faut que tous les modales sur téléphone on puisse tout faire en un clic jamais devoir
> scroll.

> Toujours la même chose en mode web app

> J'ai toujours ça

*(trois allers-retours sur le même champ de date coupé par le bord de l'écran — voir
ERREURS.md #024 et #025)*

> Attaque l'épargne

> Pour les paramètres j'aimerais les mettres dans une bulle avatar pour que derrière on
> mette les réglages selon ce qu'on veut régler avec des sous menu pour que l'ux soit déjà
> adapter au téléphone et tout faire rapidement on peut mettre le bulle avatar en haut a
> gauche de tout les écrans un peu comme ce que fait revolut

> Avec un effet de dezoom zoom dans l'avatar comme ce que fait les app iphone comme
> revolut + les pages s'ouvre toujours de la droite avec un effet de la droite vers la
> gauche fluide

> Parfait mais pourquoi ta changer les couleurs ?

> Je parle de cette palette de couleur

*(la palette d'origine a été rétablie — voir ERREURS.md #029)*

> Pourquoi ma web app est au couleur blanche maintenant ?

*(son téléphone était passé en apparence claire ; l'app n'avait aucun réglage de thème)*

> Il faudrait faire cette effet pour la bulle du compte quand on clique dessus : un effet
> d'animation d'interface appelé une transition par zoom et morphing (Shared Element
> Transition) combinée à un effet de flou d'arrière-plan (Background Blur / Frosted Glass).

> Alors c'est pas très fluide et pour l'ouverture des sous menu il doit y avoir le motion
> de la page de droite a gauche

> et quand tu reviens en arrière d'un sous menu il faut faire l'effet inverse de gauche a
> droite

> Ajoute de l'animation sur les icones de la navbar quand on appuie pour passer a une
> autre page

> Il faudrait que tu t'ajoute aussi que dans les paramètres dans gestion des comptes
> d'afficher un compte = une card et de pouvoir modifier / supprimer / ajouter un compte
> et de mettre déjà des catégorie de compte générer par nous de tout ce qui existe en
> France.

> Il faut aussi ce noter de pouvoir modifier le solde à la volé sur l'accueil

> Il manque le solde a la volée et le budget

> Et dans l'espace épargne il faut pouvoir rentrer dans le détails de chaque compte
> épargne avec l'évolution du solde et des stats de combien on place par mois et combien
> on reprend dans l'épargne pour calculer si on place trop en début de mois de l'argent et
> qu'on est obligé de reprendre ou pas etc...

> donne moi la boucle pour pouvoir avancé en autonomie


### 2026-08-20 — retours pendant la boucle autonome

> Il faut reprenser le bouton + pour moi il doit être accessible soit en haut a droite sous
> le même format que la bulle du profil ou sinon centrer dasn la navbar pour un ajout rapide

> Pareil le calendrier peut être mis en haut a droite en format bulle comme l'avatar de
> profil pas besoin de le mettre dans la navbar pour moi la navbar doit avoir :
>
> Accueil | Budget | + | Enveloppe | Epargne

*(en réponse à « qu'est-ce qu'une Enveloppe ? »)*

> Les enveloppes sont des enveloppes définit par rapport a une catégorie de dépense lié a
> l'épargne c'est pour diviser ton épargne en enveloppe visuel savoir combien tu as de
> disponible pour quoi

> Pareil dans la webapp on dois pas avoir de scroll bar visible

> Il faut également pour le solde affiché tout en haut de l'accueil soit affiche en rouge
> ou vert selon si négatif ou positif avec une petit dégradé de couleur.

> J'ai un collègue qui a développer un peu une app similaire mais j'aimerais reprendre ce
> qui nous intéresse.

*(document joint, recopié dans `docs/reference-enveloppes-collegue.md`. Périmètre tranché
en choix multiples : **tout, préparation mensuelle comprise**.)*

> Note toi dans la loop les idées que je rajoute :
>
> * Le solde d'ouverture ne dois pas être dans l'accueil on veut juste les dépenses des
>   comptes chèques et le solde
> * Le virement dois être rapide a faire aussi et on peut enlever le c'est ma paie qui n'es
>   pas utile du coup dans la partie virement
> * Dans revenue ce qui dira que c'est ma paie c'est la catégorie Salaire
> * Dans la partie Dépense il faut mettre un peu plus d'écart entre le compte et les deux
>   boutton en dessous.


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
| « c'est bug les catégories » | Deux causes distinctes : (1) le `<select>` natif ouvre sa liste avec le thème CLAIR du système sur un fond sombre — illisible ; (2) les catégories affichées étaient des restes de mes tests, antérieurs à l'isolation de la base de démonstration. Les deux sont corrigées. |
| « la navbar : l'idée était bonne, l'effet et la couleur pas assez premium » | Le rail plein hauteur est **conservé**. Ce qui change : verre nettement plus discret (le bloc était un aplat bleu sans profondeur), liseré fin et lumineux plutôt qu'une bordure épaisse, espacement plus généreux, item actif marqué par un fond translucide et un indicateur latéral au lieu d'un aplat plein. Le premium vient de la retenue, pas de l'intensité. |
| « navbar moins bleue, qui se fond avec le fond » | Le bleu ne venait pas de la teinte du verre (elle est blanche) mais de la **saturation** du `backdrop-filter` : à 190 %, il ravivait le bleu du fond au lieu de le laisser passer. Le rail descend à 105 % et sa teinte à un tiers — il se fond au lieu de se détacher. |
| « boutons : contour + dégradé » | Deux tokens ajoutés, auteurs uniques : `--degrade-accent` (dégradé vertical subtil) et `--contour-clair` (liseré interne d'un pixel). Le contour est **interne** (`inset`) : un contour externe agrandirait la cible et casserait l'alignement des rangées de boutons. |
| « essaye cette palette : #FFF4BF #FFBEFB #DC95FF #8C56D4 » | Palette lavande appliquée. Mesure faite avant de coder : `#8C56D4` donne **4,53:1** avec du blanc — il passe le seuil AA de justesse et devient donc le seul des quatre à pouvoir porter du texte clair. Les trois autres (crème, rose, mauve clair) sont trop lumineux : ils vont aux lueurs, aux liserés et aux pastilles de catégorie, jamais à un libellé sur fond coloré. |
| « un vrai calendrier avec les logos des abonnements et la fréquence » | L'agenda passe d'une liste à une **grille mensuelle**. Chaque échéance porte une pastille de marque et sa fréquence en toutes lettres (« tous les mois », « tous les ans »). Les logos viennent d'une bibliothèque locale, sans appel réseau : récupérer un favicon en ligne enverrait à un tiers la liste de tes abonnements. |
| *(mesure qui contredit la décision « bibliothèque locale de logos »)* | `simple-icons` ne contient que **7 marques sur 18** d'abonnements courants en France, pour **25 Mo** de dépendance. Les absentes sont les plus fréquentes en prélèvement : Free, SFR, EDF, Canal+, Amazon Prime, Disney+, Engie. Remplacé par des **pastilles de marque générées** — initiale et couleur stable dérivée du nom : couverture 100 %, zéro dépendance, zéro question de marque déposée. Des logos réels restent ajoutables plus tard, marque par marque. |
| « Agenda → Calendrier, prélèvements seulement » | L'écran ne crée ni n'affiche plus aucun revenu : c'est une page de **charges**. La bascule Prélèvement/Revenu disparaît de la feuille, le montant est toujours négatif, et le calendrier filtre les montants positifs. Les revenus récurrents restent possibles côté API (pas de régression), simplement l'interface ne les propose plus ici — un salaire se saisit à l'accueil, coché « c'est ma paie ». |
| « prendre en compte tous les types de prélèvement » | Raccourcis explicites dans la feuille : mensuel, trimestriel, semestriel, annuel, hebdomadaire, plus un mode libre « tous les N ». Le moteur les gérait déjà (unité × intervalle) — ce qui manquait, c'était de les **nommer** : personne ne traduit « tous les 3 mois » en « intervalle 3, unité mois » sans hésiter. |
| « penser simple, efficace, smartphone d'abord » | Règle de conduite permanente, inscrite dans `docs/UX.md`. |
| « supprimer un prélèvement » puis « Modifier/Ajouter/Supprimer » | **Fait** : liste des prélèvements avec crayon et corbeille, confirmation avant l'arrêt. Une modification ne réécrit PAS les prélèvements déjà passés — un abonnement dont le tarif augmente n'a pas coûté davantage les mois précédents. |
| « le calendrier aussi sur tablette et téléphone » | **Fait** : la grille s'affiche partout. Sous 600 px, les libellés cèdent la place à des points, et taper une case révèle le détail du jour en dessous. Sept colonnes sur 390 px donnent des cases de 48 px : assez pour un numéro et des points, pas pour un mot. |
| « une vraie bibliothèque d'icônes » | **Fait** : `lucide-react`, tree-shakable. Coût mesuré : +8 ko gzip au bundle. Les glyphes Unicode ont disparu — un caractère change de dessin selon la police du système et ne s'aligne jamais deux fois pareil. |
| « chercher le logo sur internet depuis le site officiel » | **En attente d'arbitrage.** Faisable, mais la requête doit partir du SERVEUR et non du navigateur, avec cache : sinon chaque logo révèle à un tiers, depuis ton adresse IP, quels abonnements tu as. Question posée. |
| « à venir = le mois en cours, non encore passé » | **À faire** : la section liste aujourd'hui 60 jours glissants. À restreindre aux échéances du mois civil en cours postérieures à aujourd'hui. |
| « modifier / supprimer une dépense, et voir son détail » | **À faire** : l'API n'a ni PATCH ni DELETE sur les opérations. À ajouter des deux côtés, avec la même règle que les catégories — confirmation avant suppression. |
| « surtout prévu pour mobile & tablette » | Mobile-first strict : `min-width` uniquement, tab bar basse, safe areas, cibles ≥ 44 px. |

## État du chantier

**Au 2026-08-20.** Ce bloc décrit l'état RÉEL. S'il diverge du code, le code a raison.

**Livré et vérifié** : authentification et foyer ; comptes privés avec catalogue de
produits français ; catégories ; opérations (créer, modifier, supprimer, détailler) ;
période de paie à paie ; récurrences et calendrier ; plafonds par catégorie AVEC leur
écran et les jauges de l'accueil ; virements entre comptes ; page Épargne ; correction du
solde par ajustement ; bulle d'avatar et paramètres en sous-menus ; thème au choix ;
mouvement des écrans mesuré à 60 images/s.

**Reste à faire**, dans cet ordre :

1. ~~Détail d'un compte d'épargne~~ — **fait le 2026-08-20**.
2. **Enveloppes** — chantier découpé en quatre lots, tranché le 2026-08-20 d'après
   `docs/reference-enveloppes-collegue.md`. La règle qui commande tout le reste :

   > Une allocation vers une enveloppe ne crée JAMAIS de mouvement bancaire.

   Compte ≠ enveloppe ≠ budget. Le compte dit où l'argent EST, l'enveloppe à quoi il est
   PROMIS, le budget ce qu'on prévoit d'y mettre.

   - **E1 — noyau.** Table `enveloppe` (nom, catégorie, compte préféré, cible, date cible)
     et **journal de mouvements** : aucun solde stocké, il se recalcule — c'est déjà la
     règle du projet pour les comptes. Une enveloppe peut passer en négatif, et le total
     réservé ne compte que les soldes POSITIFS : une enveloppe dans le rouge ne doit pas
     rogner ce que les autres promettent. Onglet Enveloppe.
   - **E2 — couverture par compte.** Solde théorique attendu d'un compte = somme des
     enveloppes qui le désignent. Comparé au solde réel : correct, excédent, insuffisant.
     Répond à « mes promesses sont-elles couvertes », sans import bancaire.
   - **E3 — préparation mensuelle.** À chaque paie, proposition de répartition :
     `place = max(0, cible − actuel)`, `recommandé = min(budget mensuel, place)`,
     `libéré = budget − recommandé`. Le libéré n'est JAMAIS déplacé tout seul : il est
     présenté comme disponible. Validation → mouvements d'allocation.
   - **E4 — déclaration de virement.** « J'ai fait ce virement » est une DÉCLARATION, pas
     une transaction. Elle reste en attente jusqu'à confirmation. Sans import bancaire,
     la seule confirmation possible est la correction manuelle du solde, déjà en place —
     **à écrire noir sur blanc dans l'écran** plutôt que de laisser croire à un
     rapprochement automatique.

3. **Nouvelle barre d'onglets**, demandée le 2026-08-20 :
   `Accueil | Budget | + | Enveloppe | Épargne`. Le **+ est centré** dans la barre — c'est
   le geste le plus fréquent, il tombe sous le pouce. Le **Calendrier** quitte la barre
   pour une bulle en haut à droite, au format de celle du profil. Budget devient un
   onglet à part entière au lieu d'un écran poussé depuis l'accueil.
   *(« Enveloppe » reste à définir, voir Points ouverts.)*
4. **Retouches de la saisie et de l'accueil**, demandées le 2026-08-20 :
   - le **solde d'ouverture** ne doit pas figurer dans la liste de l'accueil : on y veut
     les dépenses des comptes chèques et le solde, pas la ligne d'amorçage ;
   - la case **« c'est ma paie » disparaît du mode Virement**, où elle n'a aucun sens ;
   - en mode **Revenu**, c'est la catégorie **Salaire** qui dit que c'est la paie ;
   - plus d'**écart** entre le sélecteur de compte et les deux boutons, en mode Dépense.
5. **Onglet Foyer** — membres, codes d'invitation (aujourd'hui enfouis dans un sous-menu),
   comptes joints, plafonds partagés. C'est le lot 5 du séquencement d'origine.
3. **Logos des prélèvements**, sur le modèle KeePassXC : bouton explicite, requête faite
   par le serveur, mise en cache, repli sur la pastille.
4. **Total annuel des charges** — « mes abonnements me coûtent X € par an » est
   l'information qui fait résilier.
5. **Réglages restants** : `paies_par_cycle` (la colonne existe, aucun écran ne l'expose),
   archiver une catégorie (l'API le permet déjà).
6. **Déploiement VPS** — ne se fait PAS sans accord explicite d'Olivier.

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

- ~~Ce qu'est une « Enveloppe »~~ — **TRANCHÉ le 2026-08-20** : une enveloppe découpe
  l'ÉPARGNE, pas le budget. Elle est rattachée à une catégorie de dépense et répond à
  « combien ai-je de disponible pour quoi ». Elle ne déplace aucun argent : c'est une
  partition de ce qui est déjà sur les livrets. **Invariant à tenir** : la somme des
  enveloppes ne peut jamais dépasser l'épargne réelle, et le non-affecté est toujours
  affiché. Sans cette contrainte, le système devient une fiction qui promet de l'argent
  qui n'existe pas — c'est l'échec classique de la méthode des enveloppes.
- **« C'est la catégorie Salaire qui dit que c'est la paie » contredit une règle écrite.**
  `models/budget.py` dit noir sur blanc : « Le déduire d'une catégorie nommée *Salaire*
  rendrait la règle invisible et cassable en renommant. » Une paie ouvre la période
  budgétaire ; si renommer une catégorie déplaçait les périodes, des mois clos
  changeraient de bornes après coup. Proposition de compromis à valider : garder le
  marqueur explicite en base, mais le **pré-cocher automatiquement** quand la catégorie
  choisie est Salaire — l'utilisateur n'y pense plus, la donnée reste explicite.

- **Période budgétaire quand les comptes joints arriveront** : les plafonds du foyer
  auront besoin d'une période commune, alors que chaque membre aura la sienne (sa paie).
  À trancher au lot du partage, pas avant.
- **Ancrage du premier cycle** : quand `paies_par_cycle` > 1, quelle paie ouvre le tout
  premier cycle ? Ensuite la règle se déduit (celle qui suit la fin du cycle précédent),
  mais l'amorçage demande un choix de l'utilisateur — à traiter au lot 2.

- Expo vs Flutter — tranché après le lot 4.
- Liste de catégories par défaut ou libre — au lot 2.
- Sort des opérations sans catégorie vis-à-vis des plafonds — au lot 4.

## Prompt de boucle

À coller après `/loop` pour me laisser avancer seul. Il est écrit ici et non ailleurs
pour qu'il vieillisse avec le chantier : la liste des tâches vit dans « État du chantier »
ci-dessus, et le prompt s'y réfère au lieu de la recopier.

```
Avance seul sur mycounts. Prends la PREMIÈRE tâche non faite de « Reste à faire » dans
BOUCLE.md, finis-la entièrement, puis passe à la suivante.

Avant de coder :
- relis ERREURS.md, en entier si tu touches une zone où je me suis déjà trompé ;
- écris ce que l'écran fait ET ce qu'il ne fait pas avant d'écrire une ligne — trois
  écrans ont été refaits deux fois faute de l'avoir fixé avant.

Pour chaque changement :
- une mesure qui ne peut pas rendre la réponse inverse ne prouve rien. Deux grandeurs qui
  varient en sens OPPOSÉS, plus un témoin qui ne doit pas bouger ;
- tout témoin est vérifié PAR MUTATION : casse l'implémentation, vois-le rougir, restaure.
  Un test jamais vu rouge n'est pas un test ;
- vérification verte avant d'ouvrir le lot suivant : make verifier, make tests-integration,
  make tests-e2e, make front-tests. Deux fois de suite pour l'e2e, la base est partagée ;
- la doc part dans le même commit que le code, le code mort se supprime au passage ;
- une entrée docs/changelog.d/ par changement, et ERREURS.md à chaque fois que je me
  trompe — surtout quand la mesure portait sur le mauvais sujet ;
- commit et push sans me redemander.

Arrête-toi et demande-moi :
- toute décision de DIRECTION ARTISTIQUE — couleur, palette, densité, ton. J'ai changé
  une couleur pour faire passer un contrôle, c'était mon erreur (ERREURS.md #029) ;
- tout ce qui touche au VPS de production ;
- toute suppression de données qui ne soit pas la mienne.
Pose-les en choix multiples, avec les chiffres, jamais en prose.

Pièges déjà payés, à ne pas repayer :
- la base de DÉMONSTRATION se migre séparément (make demo-migrer). L'API refuse
  désormais de démarrer si elle est en retard ;
- ce dépôt n'a pas de configuration prettier par défaut : le style est guillemets simples,
  sans point-virgule, 100 colonnes. frontend/.prettierrc l'écrit ;
- un module CSS renomme aussi les `animation-name` : une image clé partagée vit dans
  global.css et s'applique par une CLASSE globale ;
- les tests e2e partagent une base : n'écris jamais un test qui suppose un état vide sans
  le garantir lui-même ;
- iOS ne rend pas les champs natifs comme Chromium. Ce que tu ne peux pas observer
  localement, écris-le comme angle mort dans le test plutôt que de le supposer bon ;
- vérifie la CI en sélectionnant par headSha == git rev-parse HEAD, et lis les compteurs :
  un job vert dont les tests ont été skippés ne prouve rien.

Rends compte en une fois quand la tâche est finie : ce qui est livré, ce qui a été mesuré
et avec quels chiffres, ce que tu as trouvé en chemin, ce qu'il me reste à vérifier sur
mon téléphone.
```
