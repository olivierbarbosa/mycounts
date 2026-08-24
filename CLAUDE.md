# mycounts

Application de gestion de budget de foyer : saisie des dépenses et des revenus, agenda
des prélèvements, plafonds par catégorie.

**Ce fichier décrit l'état RÉEL du projet.** S'il diverge du code, le code a raison et ce
fichier se corrige dans le même commit. Toute ligne ici doit pointer vers un fichier
existant : une ligne sans fichier est une intention, sa place est dans le plan ou dans
`BOUCLE.md`.

## État

**Livré** : authentification et foyer ; comptes privés ; catégories (créer, renommer,
retinter, archiver, supprimer — et **créer à la volée** depuis la saisie ou les budgets) ;
opérations (créer, modifier, supprimer, détailler) ; période budgétaire de paie à paie ;
soldes et liste ; amorçage avec solde d'ouverture ; récurrences, matérialisation
idempotente, calendrier mensuel et file « à confirmer » ; plafonds par catégorie avec leur
écran et les jauges de l'accueil ; virements ; page Épargne et détail d'un livret ;
correction du solde par ajustement ; enveloppes avec leurs réglages et la préparation
mensuelle ; statistiques et constats chiffrés ; import de relevé CSV avec écran de revue ;
profil personnel — nom, adresse, mot de passe — et **image de profil**.
Interface Liquid Glass sur palette **bleu ardoise**, mobile d'abord, rail latéral au-delà
de 1024 px. Barre d'onglets à deux capsules (modèle Apple Music) ; écrans ouverts depuis
une bulle du haut, avec glissement de retour au doigt. Onglet Foyer : bascule entre
comptes personnels et comptes joints, liste des membres, invitation, dissolution du
partage et suppression définitive de son compte.

**Manque** : couverture des enveloppes par compte, au sens du rapprochement — où
l'argent EST contre où il devrait être (lot E2) ; MFA obligatoire dans l'onboarding et
appareils de confiance — le TOTP, ses codes de secours et l'anti-rejeu sont livrés ; mot
de passe oublié ; chiffrement des libellés et des noms — les montants restent en clair,
sans quoi soldes et plafonds quitteraient SQL (tranché le 22 août 2026) ; quitter un
foyer ; historique des corrections de solde ; logos et icônes PWA.

**Déploiement**, livré le 24 août 2026 : `infra/docker-compose.vps.yml`, un seul fichier
pour la production et la préproduction, qui ne diffèrent que par leur fichier
d'environnement — deux descriptions séparées divergeraient exactement là où dev et prod
doivent se ressembler. `mycounts.app` en production, `dev.mycounts.app` en
préproduction, derrière le Traefik déjà en place sur le VPS.

**Le front et l'API partagent le même nom d'hôte, et ce n'est pas négociable** : le
cookie de session est `samesite=lax` et le projet n'a AUCUNE configuration CORS. Traefik
envoie `/api` vers l'API et le reste vers nginx. `/health` reste interne à Docker :
l'exposer permettrait de consommer le pool PostgreSQL depuis Internet. Un sous-domaine
`api.` — que les enregistrements DNS laissaient croire — casserait l'authentification.

**Le seul proxy fiable est `luminapp_traefik`.** `infra/demarrer-api.sh` résout son IP au
démarrage et la passe à `--forwarded-allow-ips`; la valeur `*` est interdite, car elle
permettrait à un client de choisir lui-même l'origine utilisée par l'anti-bruteforce.
`MYCOUNTS_CLE_HMAC_AUTH` doit contenir au moins 32 caractères aléatoires dans les deux
fichiers d'environnement du VPS avant le premier déploiement de ce lot.

Le déploiement est **tiré, pas poussé** : un timer systemd compare toutes les
5 minutes `origin/main` et `origin/dev` aux deux arbres de travail du VPS
(`~/mycounts` et `~/mycounts-dev`) et ne reconstruit que si la révision a bougé.
Rien d'extérieur n'obtient de droit sur la machine. `infra/deployer-auto.sh` retient
le commit qui a échoué et ne le rejoue pas en boucle ; `infra/deployer.sh` prend le
verrou lui-même, de sorte qu'une exécution manuelle et le timer ne peuvent pas se
croiser — faute constatée sur luminapp le 17 août 2026, deux `alembic upgrade head`
concurrents sur la même base. La base est sauvegardée avant toute migration, et une
sauvegarde de moins de 512 octets arrête le déploiement. Le timer ne déploie un commit
qu'après le succès du job GitHub Actions `verifier` sur ce SHA exact ; `main` et `dev`
passent tous deux cette CI.

Deux pièges payés au premier déploiement : `httpx` était déclaré en dépendance de
DÉVELOPPEMENT alors que `categorisation_ia.py` l'importe au chargement du module, si
bien que l'API ne démarrait pas — invisible en local comme en CI, qui installent tous
deux `.[dev]`. Et `app.py` localise `alembic.ini` par `Path(__file__).parents[3]` : il
lui faut l'arborescence source, donc l'image installe en éditable. Déplacer ce fichier
casserait le démarrage sans qu'aucun test ne le voie.

**Simplifier l'écran des enveloppes**, demandé le 22 août 2026 : il doit s'adresser à
quelqu'un qui a du mal à épargner, pas à quelqu'un qui connaît déjà le vocabulaire.
« Rollover », « usage », « priorité », « non affecté » sont des mots du modèle, pas de la
vie. Chaque réglage doit dire ce qu'il change POUR L'UTILISATEUR, et l'écran doit se lire
sans avoir rien appris au préalable.

**Import PDF : pas encore livré.** La V1 doit accepter les PDF officiels des banques avec
aperçu et refus sûr en cas de doute ; Revolut et Caisse d'Épargne seront les deux profils
certifiés de départ. Le CSV reste le chemin le plus fiable et le seul actuellement livré.

**Limite actuelle : un utilisateur appartient à UN seul foyer.** `Utilisateur.foyer_id`,
non nullable. La vue
« comptes joints » est un FILTRE sur `Compte.prive`, pas une entité : il n'existe pas
d'espace partagé à créer, quitter ou supprimer séparément. La V1 lèvera cette limite avec
`Espace` et `Appartenance` : le compte devient l'identité stable, puis la personne crée ou
rejoint plusieurs foyers entièrement isolés. Cela demande une réécriture explicite de tout
le périmètre ; elle est planifiée dans `docs/V1-ARCHITECTURE.md`.

Le plan d'exécution détaillé vit dans `docs/PLAN.md` — il fixe pour chaque écran ce qu'il
fait **et ce qu'il ne fait pas**. Cette seconde colonne existe parce que trois écrans ont
été refaits deux ou trois fois faute de l'avoir écrite avant de coder.

## Stack

Python 3.12 · FastAPI · PostgreSQL 16 · SQLAlchemy 2 · Alembic · React + Vite +
TypeScript · CSS Modules · Playwright. Tout est en français : noms de fonctions, de
variables, de composants et de tests.

## Commandes

```bash
make installer          # venv + dépendances
make db-haut            # PostgreSQL sur le port 5434 + migrations (5433 est pris ailleurs)
make verifier           # lint + types + garde-fous + tests unitaires
make tests-integration  # tests contre le vrai PostgreSQL
make tests-e2e          # mise en page sur 390/820/1280 px dans un vrai navigateur
```

La liste des contrôles vit dans le `Makefile` et nulle part ailleurs ; la CI l'appelle.

## Règles en vigueur

- **Un montant est un entier de centimes** — `Cents` dans `backend/mycounts/domain/montants.py`.
  Aucun flottant dans `domain/`, vérifié par `scripts/verifier_pas_de_float.py`.
- **Les dates civiles sont en Europe/Paris** — `backend/mycounts/domain/calendrier.py`.
  En SQL, toujours `AT TIME ZONE 'Europe/Paris'`, jamais `::date` nu : le cast nu dépend
  du fuseau de session du serveur (mesuré, voir `tests/integration/test_socle_base.py`).
- **`bornes_du_mois()` est le mois CIVIL**, pas la période budgétaire — celle-ci vit dans
  `domain/periode.py` et va de paie à paie. Ne jamais utiliser l'un pour l'autre.
- **Un solde d'ouverture est une opération** (`est_ouverture`), pas une colonne. Il compte
  dans les soldes, jamais dans les dépenses — **ni dans ce qui empêche de supprimer un
  compte** : un compte qui ne porte que son amorçage n'a clos aucun mois, et le refuser
  rendait irréversible la seule erreur qu'on fait vraiment (ERREURS.md #042).
- **La nature d'une catégorie (dépense / revenu) n'est pas modifiable** : la changer
  inverserait le signe attendu des opérations déjà classées, et donc des mois clos.
- **Toute l'API vit sous `/api`** — un seul préfixe, aucune liste de chemins à
  synchroniser avec le proxy de développement.
- **Deux mondes étanches : ses comptes, ceux du foyer.** La vue fait partie du PÉRIMÈTRE
  (`Principal.vue`), pas de l'affichage : une fonction qui l'oublierait rendrait des
  comptes qui ne sont pas les siens. Son défaut est PERSONNELLE — au pire on montre à
  quelqu'un ses propres comptes ; l'inverse ferait fuiter par omission.
- **Toute requête passe par `backend/mycounts/repository/`** — `scripts/verifier_scope_repository.py`
  refuse tout `select`/`execute` écrit ailleurs dans `backend/mycounts/`. Chaque lecture
  de données de foyer prend un `Principal` : le périmètre n'est jamais implicite.
- **Aucune inscription publique.** Premier compte par `scripts/creer_premier_compte.py`,
  les autres par code d'invitation (haché, usage unique, 7 jours).
- **Un foyer a UN propriétaire** — `Utilisateur.est_proprietaire`, index unique partiel
  déclaré dans la migration seule (un `WHERE` exigerait un `text()`, que le garde-fou n°7
  refuse hors du repository — même convention que `Plafond`). C'est celui qui a créé le
  foyer. Lui seul peut le détruire, parce que le foyer contient les données de TOUS ses
  membres. Une colonne explicite, jamais « le membre le plus ancien » : un pouvoir déduit
  d'une date de création est une règle sans auteur.
- **Arrêter de partager et disparaître sont deux actions, sur deux écrans.** Les
  confondre faisait perdre son compte à qui voulait seulement la première (ERREURS.md
  #044). `DELETE /auth/foyer/partage` supprime les comptes JOINTS et rien d'autre — pas de
  déconnexion, pas de perte des comptes personnels ; refusé si l'un porte de vraies
  opérations, et le message les nomme. `DELETE /auth/moi` efface son compte, et emporte le
  foyer seulement si c'est le dernier membre. Le propriétaire ne part pas tant qu'il reste
  des membres : `Compte.proprietaire_id` pointerait vers un effacé, et plus personne ne
  pourrait supprimer les comptes joints qu'il a ouverts.
- **Une destruction se confirme en retapant ce qu'elle détruit** — l'ADRESSE pour son
  compte, jamais le nom du foyer, qui désignait la mauvaise chose. La barrière ne vise pas
  celui qui veut détruire, mais celui qui ne le veut pas et dont le doigt a glissé.
  `repository/auth.supprimer_le_foyer` reste le seul endroit autorisé à tout défaire.
  Aucune sauvegarde, aucune corbeille.
- **Chaque vue montre son monde, partout.** Les rubriques des paramètres suivent la vue,
  l'écran de gestion des comptes aussi (`inclure_archives`, jamais `toutes_vues`), et le
  drapeau `prive` d'un compte neuf est DÉDUIT de la vue — jamais redemandé dans le
  formulaire, où l'on pouvait le contredire et créer un compte qui s'évaporait de la liste.
  Deux écrans qui répondraient différemment à la même bascule s'apprennent deux fois.
- **Afficher un objet est une promesse qu'on peut agir dessus.** La LISTE se resserre sur
  la vue courante, mais `compte_administrable` reste large des deux côtés : une action part
  avec l'en-tête du moment où l'on clique, et refuser dès qu'il ne concorde plus produirait
  un « introuvable » à propos de ce qui est à l'écran (ERREURS.md #043). Les écrans qui
  TOTALISENT gardent `compte_visible` : un solde ne mélange jamais les deux mondes.
- **Le foyer est un conteneur technique, pas un groupe.** Tout compte en reçoit un
  d'office (`foyer_id` non nullable) : tant qu'on est seul, l'écran dit « Partage » et non
  « Membres », et n'affiche pas une liste d'une personne. Un modèle a le droit d'avoir ses
  noms ; l'écran n'a pas le droit de les emprunter sans se demander ce qu'ils affirment
  (ERREURS.md #046). La rubrique « Foyer » n'apparaît qu'une fois un compte joint créé :
  l'espace commun naît de son premier compte, on y invite ensuite. **On ne peut pas QUITTER
  un foyer** — il faudrait un foyer d'accueil,
  le déplacement des comptes privés et la duplication des catégories, qui appartiennent au
  foyer. Seul « supprimer mon compte » existe.
- **Une action ne se propose pas quand son échec est certain.** « Dissoudre le partage »
  n'apparaît que s'il existe un compte joint : l'écran sait, avant de proposer, que le
  serveur refusera.
- **Un périmètre vide n'affiche AUCUNE mesure.** Sans compte joint, la vue foyer montre
  l'invitation et rien d'autre — pas de solde à 0,00 €, pas de jauge, pas de bouton de
  saisie. « Zéro » répond faux à une question dont la vraie réponse est « il n'y a rien à
  compter ». Mais l'écran vidé garde la bascule et « Foyer » : un état vide ne doit jamais
  emporter la porte de sortie.
- **Le libellé et le chiffre changent ENSEMBLE.** `basculerVers` attend les données du
  nouveau monde avant de poser la vue : les mettre à jour séparément affiche l'ancien
  compte sous le nouveau nom (ERREURS.md #045).
- **Un état d'attente affiché par défaut est un état d'attente qui ment.** « Rien reçu » et
  « reçu que c'est vide » sont deux faits distincts : les confondre rend la panne
  rigoureusement indistinguable du fonctionnement normal (ERREURS.md #041).
- **Une image reçue n'est JAMAIS servie telle quelle** — `domain/avatars.normaliser`
  décode, redresse selon l'EXIF, recadre en carré et réencode en WebP. Le réencodage porte
  trois garanties qu'un contrôle du type déclaré ne donne pas : c'est bien une image, les
  métadonnées partent — dont la position GPS que transporte toute photo de téléphone —, et
  la borne de taille est réelle. Stockée en base, table `avatar` à part : une seule chose à
  sauvegarder et à chiffrer, et pas cinquante kilo-octets traînés à chaque lecture de
  session. La version d'URL vient du SERVEUR : un compteur local ne rafraîchirait que
  l'écran qui l'incrémente.
- **Changer son mot de passe ferme les AUTRES sessions, jamais la sienne.** On en change
  surtout quand quelqu'un d'autre pourrait le connaître ; fermer la sienne renverrait vers
  l'écran de connexion juste après un succès, ce qui se lit comme un échec.
- **Une adresse électronique est validée par `normaliser_courriel()`**, dans le domaine.
  Le schéma d'API l'appelle via `AfterValidator` — pas d'`EmailStr`, qui ferait un second
  auteur de la règle.
- **Une échéance dit un RYTHME, un objectif sans date dit un plancher.**
  `contribution_theorique` = reste ÷ mois civils restants, arrondi au supérieur, minimum
  un mois. Elle est la TROISIÈME source de budget mensuel, après la contribution écrite et
  le plafond de catégorie : une valeur déduite ne recouvre jamais une valeur choisie.
- **La capacité d'épargne du mois est le solde PROJETÉ du quotidien**, jamais le réel —
  placer le réel viderait le compte courant juste avant l'échéance du loyer. Elle vient de
  `resume_de_la_periode`, le calcul de l'accueil, et ne s'ADDITIONNE jamais au disponible
  des enveloppes : l'un découpe l'épargne déjà là, l'autre dit ce qui pourrait la
  rejoindre.
- **Plafonds et enveloppes suivent la VUE**, comme le reste — `_plafonds_autorises` et
  `Enveloppe.vue` en sont les auteurs. Les deux n'ont pas la même règle de propriété, et
  l'unicité en base la dictait déjà : un plafond PERSONNEL n'appartient qu'à soi, un
  plafond de FOYER est commun (`uq_plafond_de_foyer_par_categorie` n'en admet qu'un par
  catégorie, tous membres confondus). La `vue` est DÉDUITE du périmètre à la création,
  jamais demandée.
- **`Operation.cree_par_id` est exposé, le nom ne l'est pas.** Le résoudre côté serveur
  imposerait une jointure sur chaque ligne de chaque liste pour un renseignement qu'on ne
  lit qu'en ouvrant une opération. L'écran de détail interroge les membres, une fois, et
  n'affiche « Saisi par » que si l'auteur est quelqu'un d'autre.
- **Le journal de l'accueil montre ce qu'on a ACHETÉ.** Ni l'amorçage ni les ajustements
  n'y figurent : tous deux comptent pleinement dans les soldes, aucun n'est une dépense.
  Conséquence assumée — cet écran étant le seul à lister les opérations, un ajustement
  n'est plus consultable une fois écrit ; il reste corrigeable, l'écart étant recalculé par
  le serveur à chaque nouvelle correction.
- **Une modale se rend par `Portail`, dans `<body>`.** Un `z-index` n'est comparable
  qu'entre frères d'un même contexte d'empilement, et les écrans d'onglet en créent un —
  leur animation conserve un `transform`, fût-il l'identité. Une feuille écrite dans un
  écran passait donc sous la barre de navigation avec le bon numéro de plan (ERREURS.md
  #049).
- **Un virement n'est ni une dépense ni un revenu** : l'argent change de poche sans
  quitter le foyer. Il reste dans les soldes des deux comptes, sort des dépenses et des
  plafonds.
- **Une classe utilitaire ne déclare rien que son consommateur puisse vouloir
  contredire** — deux incidents pour la même cause (ERREURS.md #008 et #020).
- **Une sonde de mesure a un domaine de validité** : le connaître avant de croire son
  verdict. Celle du contraste m'a trompé trois fois (#011, #021).
- **Frontend : `design/tokens.ts` est l'auteur unique de la palette ET de l'ordre
  d'empilement.** Les composants n'écrivent que `var(--…)`, y compris pour les `z-index` :
  ils choisissent un RÔLE (`--plan-feuille`, `--plan-ecran`…), jamais un nombre. Deux
  nombres choisis dans deux fichiers avaient rendu un formulaire invisible derrière l'écran
  qui l'ouvrait (ERREURS.md #038).
- **DA Liquid Glass sur palette bleu ardoise** — `#334155`, `#0EA5E9`, `#7DD3FC`,
  `#E0F2FE`, `#F1F5F9`. Un texte PEUT être posé sur du verre, à une condition mesurée —
  contraste AA de 4,5:1 vérifié dans les deux thèmes et les trois positions de transparence
  (`frontend/e2e/contraste.spec.ts`). Les opacités de texte et la teinte de l'accent sont
  donc contraintes par la mesure, pas choisies à l'œil : `#0EA5E9` ne porte AUCUN texte
  (2,77:1 avec du blanc) et s'assombrit même en thème clair pour tenir le seuil des
  composants graphiques.
- **Le contraste se mesure sur le RENDU, jamais sur un aplat.** Un montant n'est pas posé
  sur le fond mais sur le fond + le halo + le verre. Un calcul entre deux valeurs
  hexadécimales a pour domaine de validité « deux aplats opaques » — ce n'est pas cette
  interface. Trois erreurs pour cette seule cause (#011, #021, #035).
- **Mobile d'abord, bureau à part entière.** Media queries `min-width` uniquement. À
  partir de 1024 px la navigation devient un rail latéral — pas une tab bar centrée dans
  le vide.
- **Session en cookie `httponly` + `samesite=lax`**, jamais en `localStorage`. Une adresse
  inconnue et un mot de passe faux produisent la même réponse ET le même temps de réponse
  (empreinte-leurre Argon2 — sans elle, l'écart mesuré est de 12,5×).

## Garde-fous actifs

Onze — dix bloquants et un avertisseur — tous prouvés en les faisant échouer devant la faute qu'ils
prétendent détecter — **y compris les cibles du `Makefile` elles-mêmes** : `front-lint` a
été vert sans rien vérifier pendant toute la vie du projet, faute de `-p` sur un tsconfig
de références (ERREURS.md #034) : données bancaires (IBAN mod-97, PAN Luhn), secrets, dépendances LLM,
tête Alembic unique, flottants dans le domaine, requêtes hors repository, couleurs en dur
hors `tokens.ts`, et mise en page sur trois tailles d'écran. Le onzième avertit quand la base de
DÉMONSTRATION est en retard sur les migrations : elle se migre séparément, son API refuse
alors de démarrer, et l'application n'affiche plus rien (ERREURS.md #039). Chaque script documente en
tête **ce qu'il ne détecte pas** — lire cette section avant de lui faire confiance.

## Habitudes

- Une mesure qui ne peut pas rendre la réponse inverse ne prouve rien. Avant d'accepter un
  test ou un chiffre : *dans quel cas aurait-il donné l'autre résultat ?* Si la réponse est
  « aucun », l'exécuter contre l'implémentation fautive.
- Valider par le chemin de production : PostgreSQL réel, pas SQLite ; l'écran, pas `curl`.
- **Vérification verte AVANT d'ouvrir le lot suivant**, toujours : `make verifier`,
  `make tests-integration`, `make tests-e2e`, puis la CI réellement passée. Deux pièges,
  tous deux rencontrés : un job vert dont les tests ont été *skippés* ne prouve rien
  (lire les compteurs), et `gh run list --limit 1` renvoie souvent l'exécution du commit
  PRÉCÉDENT — sélectionner par `headSha == git rev-parse HEAD`.
- `ERREURS.md` se relit avant de toucher une zone où je me suis déjà trompé. La forme la
  plus fréquente, cinq entrées sur dix-sept : *la mesure porte sur le mauvais sujet* —
  mauvaise machine, mauvais port, mauvais commit, mauvais état du serveur.
- **Un témoin qui modifie du code serveur exige un redémarrage d'uvicorn** avant d'être
  cru, et une vérification que le fichier est bien restauré ensuite (ERREURS.md #017).
- Une donnée a **un** auteur. Ne jamais recopier une liste, une constante ou une règle
  dans une seconde fonction.
- La doc part dans le même commit que le code. Le code mort se supprime au passage.
