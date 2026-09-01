# mycounts

Application de gestion de budget de foyer : saisie des dépenses et des revenus, agenda
des prélèvements, plafonds par catégorie.

**Ce fichier décrit l'état RÉEL du projet.** S'il diverge du code, le code a raison et ce
fichier se corrige dans le même commit. Toute ligne ici doit pointer vers un fichier
existant : une ligne sans fichier est une intention, sa place est dans le plan ou dans
`docs/V1-ROADMAP.md`.

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
une bulle du haut, avec glissement de retour au doigt. Le sélecteur d'espace passe en un
geste du personnel à chacun des foyers ; le changement de libellé et de données est
atomique. Les routes historiques de « vue comptes joints » restent compatibles pendant la
migration, sans définir le nouveau périmètre.

**Identité livrée le 24 août 2026** : le second facteur est OBLIGATOIRE — une session
sans TOTP satisfait n'obtient que les routes `/auth` (`principal_identite`), et les routes
financières (`principal_courant`) répondent 403 avec un motif machine-lisible tant que
l'adresse n'est pas vérifiée et le TOTP activé ; parcours d'enrôlement dédié
(`frontend/src/ecrans/EnrolementMfa.tsx`) avec codes de secours à confirmer ; appareils
fiables trente jours (`repository/identite.py`, cookie `samesite=strict`, secret tourné à
chaque usage) ; vérification d'adresse et mot de passe oublié par jetons opaques à usage
unique ; inscription publique fermée par `MYCOUNTS_INSCRIPTIONS_OUVERTES=false` ; boîte
d'envoi transactionnelle et worker SMTP `scripts/traiter_courriels.py`, service `courriels`
du compose VPS. Migration `e18c7d41a2b0_identite_publique.py`.

**Manque** : couverture des enveloppes par compte, au sens du rapprochement — où
l'argent EST contre où il devrait être (lot E2) ; chiffrement des libellés et des noms —
les montants restent en clair, sans quoi soldes et plafonds quitteraient SQL (tranché le
22 août 2026) ; quitter un foyer.

**PWA livrée** : manifest et icônes standard/maskable ; installation guidée dans les
paramètres ; métadonnées iOS et zones sûres ; mise à jour consentie ; shell hors ligne sans
aucune réponse API financière en cache. La frontière de plateforme et la configuration
Capacitor préparent iOS/Android ; le transport natif reste volontairement inactif tant que
le trousseau et les jetons courts serveur ne sont pas livrés.

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
5 minutes `origin/main` et `origin/dev` à **la révision qui tourne**, lue sur l'étiquette
OCI `org.opencontainers.image.revision` de l'image de l'API, que `deployer.sh` estampille
à la construction. Jamais au `HEAD` des arbres de travail (`~/mycounts` et
`~/mycounts-dev`) : un arbre avancé à la main sans déploiement rendait alors le retard
invisible, et la production est restée dix commits en arrière pendant deux jours en
silence (ERREURS.md #052). Un arbre dit une intention, l'image dit un fait.
Rien d'extérieur n'obtient de droit sur la machine. `infra/deployer-auto.sh` retient
le commit qui a échoué et ne le rejoue qu'après six heures ou un nouveau commit — jamais
« plus jamais » : un jeton Docker Hub refusé une fois a bloqué la préproduction six jours
(27 août 2026). `infra/deployer.sh` prend le
verrou lui-même, de sorte qu'une exécution manuelle et le timer ne peuvent pas se
croiser — faute constatée sur luminapp le 17 août 2026, deux `alembic upgrade head`
concurrents sur la même base. La base est sauvegardée avant toute migration par
`infra/sauvegarder.sh`, auteur unique du `pg_dump`, et une sauvegarde de moins de
512 octets arrête le déploiement. Le timer ne déploie un commit
qu'après le succès du job GitHub Actions `verifier` sur ce SHA exact ; `main` et `dev`
passent tous deux cette CI.

**Exploitation, livrée le 2 septembre 2026** — trois timers, dont les unités vivent dans
`infra/systemd/` et s'installent par `sudo infra/installer-timers.sh` :
- `mycounts-sauvegarde` : chaque nuit à 4 h UTC, `sauvegarder.sh` puis
  `verifier-restauration.sh`, qui rejoue l'archive dans une base jetable du même
  conteneur et compare révision Alembic, nombre d'opérations, somme des centimes,
  comptes et identités. **Une archive jamais restaurée n'est pas une sauvegarde.**
  Rétention quatorze jours, SUR LE VPS — pas de copie hors site, tranché le 2 septembre
  2026 : une perte du disque emporte la base et ses sauvegardes, c'est la limite connue ;
- `mycounts-surveiller` : toutes les 5 minutes, `surveiller.sh` mesure santé de l'API et
  du worker, courriels en attente depuis plus d'une heure, HTTPS par Traefik, retard de
  déploiement de plus d'une heure, sauvegarde de plus de 26 heures, 5xx des cinq
  dernières minutes, disque au-delà de 85 % ;
- les alertes partent en **push sur le téléphone** par `infra/alerter.sh`, seul point de
  sortie, vers l'URL ntfy de `MYCOUNTS_ALERTE_URL` dans chaque `.env.<pile>`. Une alerte
  est un CHANGEMENT d'état : une panne se signale une fois, son retour à la normale une
  fois, et le silence est l'état normal. Le lundi à 8 h, un battement dit que la
  surveillance elle-même est vivante — sans lui, un timer mort ressemblerait à une
  machine en parfaite santé. Aucune donnée financière, aucune adresse dans un message.

Le worker de courriels porte SA sonde : un battement de cœur écrit à chaque tour de
boucle, relu par le compose. La sonde héritée de l'image interrogeait un port qu'il
n'ouvre pas, et l'a déclaré malade six jours sans rien mesurer (ERREURS.md #054). L'API
journalise chaque 5xx avec l'identifiant `X-Mycounts-Requete` qu'elle rend au client
(`api/journalisation.py`) : la ligne du journal et la capture d'écran portent le même.

**Préproduction, règle proposée le 2 septembre 2026, à confirmer** : tout commit qui porte
une migration ou touche l'authentification passe par `dev` et se vérifie sur
`dev.mycounts.app` depuis le téléphone avant d'être poussé sur `main`. Le reste va sur
`main` directement, et `dev` est réaligné dessus par `git push origin main:dev`. Une
préproduction seize commits en retard, comme trouvée ce jour-là, ne préproduit rien.

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

**Espaces multiples livrés.** Une identité possède exactement un espace personnel et peut
créer ou rejoindre plusieurs foyers via `Espace`, `Appartenance` et
`InvitationEspace`. Le client envoie `X-Mycounts-Espace`; seul un en-tête absent choisit
le personnel, tandis qu'une valeur invalide ou non autorisée reçoit un 404 neutre. Les
finances portent `espace_id` et les liens
compte/catégorie/récurrence/enveloppe sont contraints par des FK composites. Les colonnes
`Utilisateur.foyer_id`, `Compte.prive` et `Vue` restent temporairement présentes pour la
compatibilité des anciens scripts/routes, mais aucune requête V1 ne les utilise comme
autorisation. La migration et les invariants vivent dans
`backend/migrations/versions/e31a9b6427d0_espaces_et_foyers_multiples.py`.

**La feuille de route est `docs/V1-ROADMAP.md`, et elle seule** — décidé le 2 septembre
2026, quand trois documents disaient trois suites différentes : `docs/PLAN.md` annonçait
encore l'écran Budget « à construire », BOUCLE.md datait son état du 20 août, et
`V1-PRODUIT.md` disait remplacer les deux. `PLAN.md` a été supprimé ; BOUCLE.md garde les
remarques brutes et l'historique, jamais la liste des tâches. Le principe de `PLAN.md`
survit : avant d'écrire un écran, écrire ce qu'il fait **et ce qu'il ne fait pas**, en
tête de son fichier — trois écrans ont été refaits deux ou trois fois faute de l'avoir
fait. Direction confirmée le même jour : V1-PRODUIT en entier, enveloppes migrées vers le
modèle V1 avant toute simplification de leur écran, exploitation d'abord.

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
`make tests-e2e` exige un Chromium Playwright (`cd frontend && npx playwright install
chromium`, précédé de `PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright`
sur la machine de développement, dont l'adresse IP est refusée par le CDN officiel) et
ses bibliothèques système. Sans lui, la suite est rouge en 10 ms par test — et avant le
24 août 2026, elle n'avait jamais tourné ici (ERREURS.md #050).

## Règles en vigueur

- **Un montant est un entier de centimes** — `Cents` dans `backend/mycounts/domain/montants.py`.
  Aucun flottant dans `domain/`, vérifié par `scripts/verifier_pas_de_float.py`.
- **Les dates civiles sont en Europe/Paris** — `backend/mycounts/domain/calendrier.py`.
  En SQL, toujours `AT TIME ZONE 'Europe/Paris'`, jamais `::date` nu : le cast nu dépend
  du fuseau de session du serveur (mesuré, voir `tests/integration/test_socle_base.py`).
  **Les tests aussi** : `calendrier.aujourd_hui()` côté Python, `e2e/dates.ts` côté
  Playwright (`timeZone: 'Europe/Paris'`) — jamais `date.today()` ni la zone de la
  machine. Le VPS et les runners GitHub sont en UTC : entre 22 h et minuit, leur
  « demain » est déjà l'aujourd'hui du serveur, et une échéance « à venir » se retrouvait
  matérialisée (CI rouge le 24 août 2026 à 22 h 20 UTC, sur un test vert deux heures plus tôt).
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
- **Aucune inscription publique tant que `MYCOUNTS_INSCRIPTIONS_OUVERTES` est faux** —
  son défaut. `POST /auth/inscription` répond alors 403 ; ouvert, il crée une identité
  NON vérifiée dont le seul espace initial est personnel
  (`repository/auth.creer_identite_personnelle`), et répond la même phrase que l'adresse
  soit libre ou prise. Premier compte par `scripts/creer_premier_compte.py`, les autres
  par code d'invitation (haché, usage unique, 7 jours).
- **Le second facteur n'est pas une option.** `principal_courant` refuse toute session dont
  `second_facteur_satisfait` est faux ; seules les routes `/auth` acceptent
  `principal_identite`, pour que l'enrôlement reste possible. Un test qui crée une
  identité en base passe par `connecter_avec_mfa` (`tests/integration/test_api_budget.py`),
  jamais par un simple `POST /connexion` : dix-neuf tests contournaient l'enrôlement ainsi.
  Les tests de bout en bout reçoivent une session déjà enrôlée par
  `frontend/e2e/preparation.ts` (`storageState`) — l'anti-rejeu TOTP interdit de se
  connecter par l'écran dans chaque test.
- **Un foyer a UN propriétaire** — `Utilisateur.est_proprietaire`, index unique partiel
  déclaré dans la migration seule (un `WHERE` exigerait un `text()`, que le garde-fou n°7
  refuse hors du repository — même convention que `Plafond`). C'est celui qui a créé le
  foyer. Lui seul peut le détruire, parce que le foyer contient les données de TOUS ses
  membres. Une colonne explicite, jamais « le membre le plus ancien » : un pouvoir déduit
  d'une date de création est une règle sans auteur.
- **Arrêter de partager et disparaître sont deux actions, sur deux écrans.** Les
  confondre faisait perdre son compte à qui voulait seulement la première (ERREURS.md
  #044). Depuis les espaces multiples : « Quitter ce foyer » et « Supprimer le foyer »
  vivent dans la rubrique « Foyer » d'un espace FOYER ; `DELETE /auth/moi` efface son
  compte depuis « Mon compte », qui n'existe que dans l'espace personnel. Les routes
  historiques `DELETE /auth/foyer/partage` et `Utilisateur.est_proprietaire` restent
  servies pendant la migration mais aucun écran ne les propose plus
  (`frontend/e2e/danger-compte-et-partage.spec.ts` mesure la séparation).
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
- **Le foyer est un conteneur technique, pas un groupe.** Tant qu'on est seul, l'écran
  dit « Partage » et non « Membres », et n'affiche pas une liste d'une personne. Un modèle
  a le droit d'avoir ses noms ; l'écran n'a pas le droit de les emprunter sans se demander
  ce qu'ils affirment (ERREURS.md #046). Les rubriques des paramètres suivent l'ESPACE
  actif (`Parametres.tsx`, `estFoyer`) : « Mon compte » n'existe que chez soi, « Foyer »
  que dans un foyer — chaque espace ne propose que ce qu'il administre.
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
  Les corrections se relisent donc ailleurs : `GET /comptes/{id}/ajustements`, affiché
  sous le formulaire de la feuille de correction — à côté du geste qui les produit, et non
  dans une liste de dépenses où elles feraient chercher un achat qui n'existe pas. L'ordre
  vient du repository (`date_operation DESC, cree_le DESC`) et n'est jamais refait par la
  route : corriger deux fois le même jour est le cas ordinaire, et un second tri qui
  ignorait `cree_le` restait invisible, le bon résultat arrivant quand même du premier
  auteur.
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
  qui l'ouvrait (ERREURS.md #038). **Les noms sont TOUS préfixés par leur groupe** —
  `--couleur-texte`, `--verre-flou`, `--rayon-pilule` — et le garde-fou n°12 refuse tout
  nom qui n'est pas généré : un jeton inventé ne provoque aucune erreur, seulement une
  déclaration jetée en silence (ERREURS.md #053).
- **La rangée du haut est UNE rangée.** Avatar, pilule d'espace et bulles d'action y
  partagent le même `top` et la même réserve `--disposition-reserve-bulle`. Rien ne s'y
  ajoute sur un second étage : le sélecteur d'espace l'avait fait, en `position: fixed`
  sans élargir la réserve écrite pour l'avatar seul, et recouvrait le premier titre de
  chaque écran. La pilule connaît le NOMBRE de bulles qui l'entourent, par des types
  littéraux qui refusent de compiler quand une bulle s'ajoute — un recouvrement muet ne
  se découvre autrement que sur un téléphone.
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
- **Un courriel ne part jamais depuis une requête HTTP.** L'API écrit dans
  `courriel_sortant` (`repository/identite.mettre_en_file`) dans la MÊME transaction que
  le jeton ; `scripts/traiter_courriels.py` envoie à part, avec un nombre d'essais borné,
  et ne consomme aucun essai tant que le SMTP n'est pas configuré. Aucune donnée
  financière ne figure ni dans un message ni dans un journal.

## Garde-fous actifs

Douze — onze bloquants et un avertisseur — tous prouvés en les faisant échouer devant la faute qu'ils
prétendent détecter — **y compris les cibles du `Makefile` elles-mêmes** : `front-lint` a
été vert sans rien vérifier pendant toute la vie du projet, faute de `-p` sur un tsconfig
de références (ERREURS.md #034) : données bancaires (IBAN mod-97, PAN Luhn), secrets, dépendances LLM,
tête Alembic unique, flottants dans le domaine, requêtes hors repository, couleurs en dur
hors `tokens.ts`, jetons CSS inexistants, et mise en page sur six tailles d'écran — quatre
téléphones, une tablette, un bureau. L'avertisseur signale quand la base de
DÉMONSTRATION est en retard sur les migrations : elle se migre séparément, son API refuse
alors de démarrer, et l'application n'affiche plus rien (ERREURS.md #039). Chaque script documente en
tête **ce qu'il ne détecte pas** — lire cette section avant de lui faire confiance.

Le n°12 est né d'une faute strictement muette : onze `var(--…)` désignant des jetons
inexistants, donc onze déclarations jetées par le navigateur sans une ligne de console.
Le n°9 cherche des couleurs EN DUR, l'erreur bruyante ; personne ne cherchait le nom
INVENTÉ, la silencieuse (ERREURS.md #053).

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
