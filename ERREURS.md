# ERREURS — journal des erreurs de l'agent

Ce fichier consigne **mes** erreurs (celles de l'agent), pas les bugs du produit. Il se
relit avant toute intervention sur une zone où je me suis déjà trompé.

Écrire une erreur ne produit rien de visible, et c'est précisément pourquoi on l'oublie.
Les erreurs mises côte à côte révèlent leur forme commune — que chacune prise isolément
ne montre pas.

## Format

Chaque entrée répond aux quatre mêmes questions :

1. **Ce que j'ai cru** — l'affirmation que je tenais pour acquise.
2. **Ce que j'ai mesuré** — la vérification réellement effectuée (« rien » est une réponse
   valide et fréquente).
3. **Pourquoi ça ne prouvait rien** — dans quel cas cette vérification aurait-elle donné
   le résultat inverse ? Si la réponse est « aucun », elle était décorative.
4. **Le contrôle qui aurait tranché** — la vérification qui, elle, pouvait échouer.

---

## 001 — Avoir prévu de documenter des invariants qui n'existaient pas

**Zone** : `CLAUDE.md`, rédaction du plan de socle.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que le `CLAUDE.md` du lot 0 devait énoncer les trois invariants du
projet (états d'opération, invariance du solde projeté, idempotence de la
matérialisation), parce qu'ils étaient décidés.

**Ce que j'ai mesuré.** Rien. J'ai confondu « décidé dans une conversation » avec
« présent dans le code ». Au lot 0 il n'existe ni table `operation`, ni calcul de solde,
ni job de matérialisation : deux des trois invariants n'auraient protégé aucune ligne.

**Pourquoi ça ne prouvait rien.** Aucune relecture du plan seul n'aurait pu me
contredire — un plan est cohérent avec lui-même par construction. C'est le mode d'erreur
générique : *une vérification qui ne consulte que la source de l'affirmation*.

**Le contrôle qui aurait tranché.** Pour chaque ligne de `CLAUDE.md`, exiger le chemin du
fichier qui la rend vraie. Une ligne sans fichier est une intention, pas de la
documentation — elle va dans le plan ou dans `BOUCLE.md`, jamais dans `CLAUDE.md`.

**Correction appliquée.** `CLAUDE.md` du lot 0 ne décrit que ce qui tourne. Chaque
invariant y sera ajouté dans le commit qui l'implémente et le teste.

**Généralisation.** Documenter un garde-fou avant de l'écrire ne coûte pas seulement des
tokens : cela produit un document que l'on cesse de croire, et donc de lire.

---

## 002 — Un test « anti-flottant » que l'implémentation fautive passait

**Zone** : `tests/unit/test_montants.py`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Qu'un test `parse("0,10") + parse("0,20") == parse("0,30")` prouvait
l'absence de flottant dans la conversion des montants, puisque `0.1 + 0.2 != 0.3` est
l'exemple canonique.

**Ce que j'ai mesuré.** J'ai implémenté les deux versions fautives et les ai exécutées
contre mes propres tests :

| Implémentation | mon test 0,10+0,20 | mon test 1000 × 0,10 |
|---|---|---|
| `int(float(x) * 100)` | **passe** | **passe** |
| `round(float(x) * 100)` | **passe** | **passe** |

Mes deux témoins étaient donc décoratifs : ils ne pouvaient pas rendre la réponse
inverse. J'allais construire tout le calcul monétaire sur cette fausse assurance.

**Pourquoi ça ne prouvait rien.** Je raisonnais sur un exemple mémorisé au lieu de mesurer
le comportement réel. `0.1 + 0.2 != 0.3` est vrai pour l'addition de flottants — mais mon
code ne fait pas ça : il convertit puis stocke des entiers. L'exemple canonique ne
s'appliquait tout simplement pas au chemin de code testé.

**Le contrôle qui aurait tranché — et qui est maintenant en place.** Exécuter la version
fautive contre le test. Résultat mesuré : `int(float×100)` casse 1 145 montants sur les
20 000 balayés (0,29 · 0,57 · 1,13 · 2,01 …), et `round(float×100)`, qui survit au
balayage, casse au-delà de 2^53 centimes. Il a fallu **deux** témoins pour fermer les deux
portes ; chacun seul en laissait une ouverte.

**Généralisation.** Un test écrit d'après un exemple célèbre teste l'exemple, pas le code.
La seule façon de savoir ce qu'un test rejette est de lui soumettre ce qu'il devrait
rejeter.

---

## 003 — Une justification affirmée sans être exécutée

**Zone** : `tests/integration/test_socle_base.py`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Qu'un test paramétré sur des fuseaux extrêmes (+14 h, −11 h) prouvait
qu'une colonne `DATE` ne dérive pas, « puisqu'avec un `TIMESTAMP` les fuseaux extrêmes
décaleraient la valeur d'un jour ». C'était écrit noir sur blanc dans le docstring.

**Ce que j'ai mesuré.** Après coup : j'ai implémenté la variante `TIMESTAMPTZ`. Elle donne
**exactement le même résultat stable** sur les trois fuseaux. Le contre-exemple que
j'invoquais pour justifier le test n'existait pas.

**Pourquoi ça ne prouvait rien.** Le test vérifiait une propriété vraie mais triviale — un
`DATE` n'a pas de fuseau, par définition du type. Aucune implémentation plausible ne
l'aurait fait échouer. Le docstring, lui, donnait au lecteur l'impression qu'un risque
réel était couvert : c'est pire qu'un test absent, parce qu'on cesse de chercher.

**Le contrôle qui aurait tranché — et qui est maintenant en place.** Le décalage réel ne
vient pas du type de colonne mais du **cast** : pour l'instant 2026-12-31 23:30 UTC,
`(horodatage)::date` renvoie le 31/12/2026 en session UTC et le 01/01/2027 en session
Europe/Paris, tandis que `AT TIME ZONE 'Europe/Paris'` renvoie le 01/01/2027 partout. Le
test compare désormais les deux et vérifie qu'ils **diffèrent** sur les sessions
concernées — un témoin qui casse si le contrôle cesse de distinguer quoi que ce soit.

**Généralisation.** Écrire « sinon X arriverait » dans un commentaire de test est une
affirmation testable. Tant qu'elle n'a pas été exécutée, c'est une croyance — et elle sera
lue comme une preuve par le prochain qui passe. Même forme que #001 et #002 : *une
vérification qui ne consulte que sa propre source*.

---

## 004 — Un fixture qui aurait rendu la CI verte sans exécuter un seul test

**Zone** : `tests/integration/test_socle_base.py`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que le premier passage de la CI, affiché « success » en 57 s,
prouvait que les 7 tests d'intégration avaient tourné contre PostgreSQL.

**Ce que j'ai mesuré.** J'ai lu les logs au lieu du statut. Ce coup-ci les tests avaient
bien tourné (`7 passed`, pas `7 skipped`). Mais en les lisant j'ai vu le défaut : mon
fixture appelait `pytest.skip()` quand la base est injoignable. Le jour où le service
PostgreSQL tombe en CI, les 7 tests seraient **skippés** et le job resterait **vert** —
sur les seuls tests qui touchent le chemin de production.

**Pourquoi ça ne prouvait rien.** Un `skip` est indiscernable d'un `pass` dans le statut
d'un job. La mesure « la CI est verte » ne pouvait pas rendre la réponse inverse : elle
serait verte avec les tests exécutés comme avec les tests ignorés. C'est un cas
particulièrement traître parce que le signal se dégrade **en silence et plus tard**, pas
au moment où on l'écrit.

**Le contrôle qui aurait tranché — et qui est maintenant en place.** Hors CI, la base
absente reste un `skip` (le poste local n'a pas toujours Docker démarré). Sous `CI=1`,
c'est un `fail`. Les deux branches ont été exécutées : 7 skipped en local, 7 errors sous
`CI=true`.

**Généralisation.** Un statut agrégé n'est pas une mesure. Il faut toujours vérifier
qu'un nombre a bougé — ici « combien de tests ont réellement tourné » — et non qu'un
voyant est vert. Même forme que #001 à #003, appliquée à l'outillage plutôt qu'au code.

---

## 005 — Un test d'isolation qui itérait sur une liste vide

**Zone** : `tests/integration/test_isolation.py`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Qu'itérer sur `app.routes` énumérait toutes les routes de
l'application, et donc que « chaque route privée exige une session » était vérifié pour
l'ensemble de l'API.

**Ce que j'ai mesuré.** `app.routes` ne contient que `/health`, `/docs`, `/redoc` et
`/openapi.json`. Les six routes de `/auth` vivent dans un objet intermédiaire
(`_IncludedRouter`) que FastAPI n'aplatit pas. Mon énumération renvoyait donc **une liste
vide** de routes privées : la boucle de vérification ne s'exécutait pas une seule fois,
et le test passait au vert sur les routes qui portent toute l'authentification.

**Pourquoi ça ne prouvait rien.** Une boucle `for … assert` sur une collection vide
réussit toujours. C'est le mode d'échec propre aux tests qui itèrent : ils ne mesurent
rien quand la collection est mal construite, et ils affichent la même chose que quand
tout va bien.

**Le contrôle qui a tranché — et il était déjà en place.** Le test-témoin
`test_il_existe_bien_des_routes_privees` a échoué immédiatement. Il a été écrit *pour*
ça, et c'est la première fois du projet qu'un témoin attrape une erreur avant moi. Il a
été renforcé depuis : il exige maintenant la présence nommée de trois routes connues, pas
seulement une liste non vide.

**Correction.** L'énumération part désormais du schéma OpenAPI (`app.openapi()["paths"]`)
plutôt que des attributs internes de FastAPI : c'est le contrat public, il liste
exactement ce qui est joignable, et il ne cassera pas à la prochaine montée de version.

**Généralisation.** Tout test qui boucle sur une collection doit d'abord prouver que la
collection n'est pas vide — et, mieux, qu'elle contient des éléments attendus nommément.
Sinon la mesure ne peut pas rendre la réponse inverse. Même forme que #001 à #004.

---

## 006 — Un test vert sur un état de base que le dépôt ne sait pas reproduire

**Zone** : `.github/workflows/ci.yml`, `Makefile`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que 32 tests d'intégration verts en local prouvaient que le lot 1
tenait debout. Je venais d'écrire l'invariant « valider par le chemin de production ».

**Ce que j'ai mesuré.** La CI a échoué au premier push :
`relation "session_web" does not exist`. J'avais lancé `alembic upgrade head` **à la main**
pendant le développement. Mon poste portait donc un état que le dépôt ne reproduisait pas,
et aucun de mes 32 tests ne pouvait le signaler — ils s'exécutaient tous après cette
commande manuelle.

**Pourquoi ça ne prouvait rien.** La mesure « les tests passent chez moi » ne peut pas
rendre la réponse inverse tant que l'environnement contient une étape non écrite. Ce n'est
pas le code qui était faux, c'est le périmètre de la mesure : elle englobait mon shell.

**Le contrôle qui a tranché.** La CI elle-même, sur une machine vierge. C'est le seul
endroit du projet où l'environnement est reconstruit depuis le dépôt seul, donc le seul
qui puisse détecter une dépendance à un geste manuel.

**Correction.** Cible `make migrer` (idempotente), appelée explicitement par la CI avant
les tests d'intégration, et par `make db-haut` en local — de sorte que démarrer la base
et la migrer soient un seul geste, impossible à dissocier par oubli.

**Généralisation.** « Ça marche chez moi » est une mesure dont le périmètre inclut des
choses non versionnées. La question à se poser n'est pas « est-ce que le test passe ? »
mais « **sur quelle machine, reconstruite comment ?** ». Et une conséquence directe : ne
jamais annoncer qu'un lot est terminé avant que la CI l'ait confirmé — c'est exactement
la règle « vérification verte avant d'ouvrir le lot suivant », que je venais d'inscrire
dans CLAUDE.md et que j'ai enfreinte au commit suivant.

---

## 007 — Vérifier une application… qui n'était pas la mienne

**Zone** : `frontend/vite.config.ts`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Qu'ouvrir `http://127.0.0.1:5175` après avoir démarré `npm run dev`
me montrait mycounts.

**Ce que j'ai mesuré.** Le HTML renvoyé contenait `data-app="admin"` et des noms de
thèmes (« Halo Boréal », « Signal Cyan ») qui n'existent nulle part dans ce dépôt :
c'était le back-office d'un **autre projet**. Le port 5175 était déjà pris ; Vite avait
basculé **en silence** sur 5176, et je testais l'application de quelqu'un d'autre. Second
piège d'environnement partagé de la journée, après PostgreSQL sur 5433.

**Pourquoi ça ne prouvait rien.** « Le serveur répond sur ce port » ne dit rien de
**quelle** application répond. La mesure n'avait aucun moyen de rendre la réponse
inverse : une page s'affichait, donc tout allait bien.

**Le contrôle qui a tranché — et qui est maintenant en place.** `strictPort: true` : le
démarrage échoue au lieu de glisser sur le port suivant. Et le premier contrôle d'un
parcours vérifie désormais l'identité de l'application (`<title>mycounts</title>`), pas
seulement un code 200.

**Effet de bord découvert dans la foulée.** Vite n'écoutait qu'en IPv6 (`[::1]`) alors que
le backend écoute en IPv4 : `curl 127.0.0.1` restait suspendu sans erreur. `host:
'127.0.0.1'` est désormais explicite des deux côtés.

**Généralisation.** Avant de croire une vérification, s'assurer qu'elle porte sur le bon
sujet. Un port, un hôte, une base : trois façons de mesurer soigneusement la mauvaise
chose.

---

## 008 — Un composant qui écrasait le positionnement de son hôte

**Zone** : `frontend/src/composants/Verre.module.css`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que la capture d'écran suffisait à valider la barre de navigation :
elle apparaissait bien en bas, en verre, avec le bon accent.

**Ce que j'ai mesuré.** `getBoundingClientRect()` sur la barre : `bas: 860` pour une
fenêtre de `819`. Elle dépassait de **41 px sous le bord**, ses boutons étaient
partiellement inatteignables. Et `gauche: 0, largeur: 1440` au lieu d'une pilule de
420 px. La cause : `.verre` déclarait `position: relative` pour ancrer un `::before`, et
cette règle — même spécificité, feuille chargée après — écrasait le `position: fixed` de
la barre.

**Pourquoi la capture ne prouvait rien.** Une image montre ce qui est peint dans le
cadre, pas ce qui déborde en dehors. Le regard ne peut pas rendre la réponse inverse sur
ce qu'il ne voit pas.

**Le contrôle qui a tranché — et qui est maintenant en place.** Mesure numérique de la
géométrie, puis un test Playwright sur les trois tailles : la navigation doit tenir
entièrement dans la fenêtre, être une barre basse sur téléphone et un rail vertical sur
bureau. Vérifié en réintroduisant `position: relative` : deux tests rougissent.

**Correction de fond.** Le reflet spéculaire passe par un second calque de `background`
au lieu d'un `::before`. La classe `.verre` n'impose donc plus **aucune** propriété de
positionnement — la cause disparaît au lieu d'être compensée par plus de spécificité.

**Généralisation.** Une classe utilitaire qui déclare `position` s'approprie une décision
qui appartient à son hôte. Deux auteurs pour une même propriété : c'est l'anti-pattern
n°3 sous sa forme CSS, et le dernier chargé gagne en silence.

---

## 009 — Le script créait des comptes que l'API refusait

**Zone** : `scripts/creer_premier_compte.py`, `backend/mycounts/api/schemas.py`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que la validation d'adresse était couverte : le schéma d'API utilisait
`EmailStr` de Pydantic, ce qui est la pratique courante.

**Ce que j'ai mesuré.** En donnant l'adresse `essai@mycounts.test` au script de création,
le compte est créé **sans erreur** — puis la connexion échoue en 422 : « the part after
the @-sign is a special-use or reserved name ». Le compte existait, en base, inutilisable.
Aucun de mes 119 tests ne le voyait, parce que tous utilisaient des adresses valides.

**Pourquoi ça ne prouvait rien.** Deux validateurs, deux auteurs : `EmailStr` dans le
schéma, `strip().lower()` dans le domaine. Chacun testé séparément, aucun test ne
comparait leurs frontières — et c'est précisément à la frontière qu'ils divergeaient.

**Le contrôle qui a tranché.** Un test de bout en bout, qui a utilisé un domaine `.test`
par simple hygiène (ne pas écrire un vrai domaine dans un dépôt). L'erreur a été trouvée
par accident, pas par un contrôle dirigé — c'est la chance qui a joué, et il ne faut pas
compter dessus.

**Correction.** `normaliser_courriel()` valide ET normalise, dans le domaine. Le schéma
d'API l'appelle via `AfterValidator` au lieu d'`EmailStr` : un seul auteur, donc plus de
frontière où diverger. Testé des deux côtés — adresses refusées ET adresses acceptées,
car un validateur qui refuse tout passerait le premier volet.

**Généralisation.** Quand deux chemins écrivent dans la même table, ils doivent partager
le **même** validateur, pas deux validateurs « équivalents ». « Équivalent » n'est
vérifiable que sur les cas qu'on a pensé à comparer.

---

## 010 — Une borne qui faisait disparaître de l'argent de tous les écrans

**Zone** : `backend/mycounts/domain/agregats.py`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que borner les opérations *confirmées* à aujourd'hui était la règle
générale : le solde réel doit correspondre à ce que la banque affiche, donc il s'arrête
au jour courant. J'ai appliqué cette borne aux quatre agrégats.

**Ce que j'ai mesuré.** Un test écrit dans la foulée : une dépense confirmée et datée de
demain donne 0 dans le solde réel — attendu — mais aussi **0 dans le solde projeté**.
Elle n'apparaissait donc dans aucun total : ni dans ce que j'ai, ni dans ce qu'il me
restera. De l'argent invisible sur tous les écrans jusqu'à sa date, puis qui réapparaît
d'un coup.

**Pourquoi ça ne prouvait rien.** Chaque agrégat pris isolément semblait correct. La
faute n'était visible qu'en regardant les quatre **ensemble** : aucun test ne posait la
question « cette opération apparaît-elle quelque part ? ». Un total juste et un total
absent se ressemblent — les deux affichent un nombre plausible.

**Le contrôle qui a tranché — et qui est maintenant en place.** Un témoin structurel qui,
pour chaque état et chaque date de la fenêtre, vérifie que l'opération contribue à **au
moins un** agrégat. Il ne teste aucune valeur particulière : il interdit la disparition.

**Correction.** Seul le solde réel garde la borne « aujourd'hui », parce que c'est la
grandeur du rapprochement bancaire. Les autres regardent jusqu'à la fin de la fenêtre.
Une échéance seulement *prévue* reste hors des plafonds : un plafond qui compterait ce
qui n'a pas encore eu lieu serait dépassé dès le premier jour de la période.

**Généralisation.** Quand plusieurs totaux partagent les mêmes données, tester chacun
séparément ne dit rien de leur **couverture commune**. Il faut un contrôle qui vérifie
qu'aucune donnée ne tombe entre eux — la même forme d'erreur que #005, où une collection
vide faisait passer une boucle de vérification.

---

## 011 — Une sonde de contraste qui mesurait faux

**Zone** : `frontend/e2e/contraste.spec.ts`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que ma sonde de contraste, en lisant `getComputedStyle().color` et
`.backgroundColor`, mesurait ce que l'œil reçoit.

**Ce que j'ai mesuré.** Elle annonçait 1,56:1 sur les onglets de navigation — un texte
prétendument illisible, alors qu'il l'est parfaitement. La cause : les surfaces produites
par `color-mix()` sont renvoyées au format `color(srgb 0.1 0.1 0.14 / 0.72)`, dont les
composantes vont de 0 à 1. Mon extracteur les lisait comme des valeurs 0–255 : toute
surface en verre était donc perçue comme un quasi-noir.

**Pourquoi c'était le pire cas.** Une sonde absente laisse un doute. Une sonde fausse
donne des ordres : j'allais éclaircir des couleurs qui n'avaient aucun problème, et la
correction aurait dégradé la DA pour rien. Le témoin « la sonde sait détecter un texte
illisible » ne l'a pas attrapée — il vérifiait qu'elle voit un vrai défaut, pas qu'elle
s'abstient sur ce qui va bien.

**Le contrôle qui a tranché.** Le désaccord entre la mesure et l'observation directe :
1,56:1 aurait dû être visiblement illisible sur la capture d'écran, et ne l'était pas.
C'est le seul moment du projet où l'œil a corrigé l'instrument, et non l'inverse.

**Ce que la sonde corrigée a réellement trouvé** — deux défauts authentiques, invisibles
à l'œil : `texteFaible` à 45 % d'opacité donnait 3,49:1, et le blanc sur l'accent
`#8B5CF6` donnait 4,23:1, tous deux sous le seuil AA de 4,5. Les opacités et la teinte de
l'accent ne sont donc plus choisies à l'œil : ce sont les valeurs les plus vives qui
passent encore le seuil.

**Généralisation.** Un instrument de mesure doit être étalonné dans les deux sens : sur
un cas qu'il doit rejeter **et** sur un cas qu'il doit accepter. Mon témoin ne couvrait
que le premier. Même forme que #002 — un test calibré sur un seul côté ne borne rien.

---

## 012 — J'allais rapporter la CI d'un autre commit

**Zone** : méthode de vérification, `gh run list`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que `gh run list --limit 1` juste après un `git push` renvoyait
l'exécution de ce push.

**Ce que j'ai mesuré.** Les chiffres affichés étaient « 117 tests unitaires, 32
d'intégration » — ceux du commit **précédent**. Le commit que je venais de pousser en
contenait 136 et 48. GitHub n'avait pas encore créé l'exécution : `--limit 1` a donc
renvoyé la plus récente *existante*, c'est-à-dire l'ancienne, avec un statut vert
parfaitement valide… pour un autre code.

**Pourquoi ça ne prouvait rien.** « La dernière exécution est verte » ne dit rien de
« mon commit est vert ». La mesure était juste, la question était fausse. Sans les
compteurs de tests, qui ont détonné, je l'aurais rapporté comme une vérification.

**Le contrôle qui a tranché — et qui est maintenant la méthode.** Sélectionner
l'exécution par `headSha` égal à `git rev-parse HEAD`, en attendant qu'elle apparaisse.
Jamais « la dernière ».

**Généralisation.** Troisième variante du même piège après #006 et #007 : la mesure porte
sur le mauvais sujet. Machine, port, et maintenant commit. La question à se poser n'est
pas « est-ce vert ? » mais « **vert pour quoi, exactement ?** ».

---

## 013 — Un agrégat nommé « dépenses » qui comptait les salaires

**Zone** : `backend/mycounts/domain/agregats.py`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que la table état × agrégat suffisait à définir chaque total. Elle
répondait à « quels états contribuent, et jusqu'à quelle date ». J'avais soigné son
exhaustivité, avec un test qui parcourt le produit cartésien.

**Ce que j'ai mesuré.** Sur une période contenant un salaire de 2 500 €, deux dépenses de
45,90 € et 120 €, `depenses_de_periode` renvoyait **+233 410 centimes** au lieu de
−16 590. Il sommait la paie avec les dépenses : ce n'était pas un total de dépenses, mais
un solde portant un autre nom.

**Pourquoi l'exhaustivité de la table ne prouvait rien.** Elle garantissait qu'aucune
combinaison état × agrégat n'était oubliée — et c'était vrai. Mais il manquait une
**dimension entière** : le signe des montants retenus. Un test d'exhaustivité ne peut
vérifier que les axes qu'on lui a donnés ; il est muet sur ceux qu'on n'a pas pensé à
déclarer. C'est le mode d'erreur propre aux contrôles de complétude.

**La conséquence si ça avait tenu.** Les plafonds du lot 4 se seraient alimentés de ce
chiffre. Un plafond « Courses 400 € » aurait affiché une consommation positive et n'aurait
**jamais** alerté — l'exact contraire de sa raison d'être, et une erreur qu'on ne
découvre qu'en constatant qu'aucune alerte n'est jamais arrivée.

**Le contrôle qui a tranché.** Un test qui écrit les quatre grandeurs attendues à la main,
sur un jeu contenant à la fois un revenu et des dépenses. Les trois soldes étaient justes ;
seul le quatrième chiffre a détonné. Sans revenu dans le jeu d'essai, l'erreur restait
invisible.

**Correction.** Une seconde table, `SIGNE_RETENU`, exhaustive et testée comme la première.
Plus un volet inverse : sur des données sans revenu, dépenses et solde doivent coïncider —
sinon un filtre qui exclurait tout passerait le test.

**Généralisation.** Vérifier qu'une table est complète ne dit rien de savoir si elle a les
bonnes colonnes. Et un jeu d'essai qui ne contient qu'un type de donnée ne peut pas
révéler une confusion entre les types.

---

## 014 — La même erreur qu'en #002, refaite dans l'autre langage

**Zone** : `frontend/src/composants/__tests__/montant.test.ts`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Qu'un balayage exhaustif de 20 000 montants, plus un cas « grand
montant », prouvait que le formatage côté client n'utilisait pas de flottant. J'avais
écrit dans le test, noir sur blanc : « rejette une implémentation qui passerait par
`toFixed(2)` ».

**Ce que j'ai mesuré.** J'ai implémenté la version par `toFixed(2)` et relancé la suite :
**12 tests sur 12 passent**. Aucun de mes deux témoins ne la distingue. En parcourant les
montants jusqu'à 3 000 €, l'écart entre les deux implémentations est nul ; il n'apparaît
qu'au-delà de `Number.MAX_SAFE_INTEGER`, c'est-à-dire là où le `number` lui-même ne
représente déjà plus l'entier reçu du serveur.

**Pourquoi c'est plus grave que #002.** C'est exactement la même erreur, sur exactement le
même sujet, quelques heures après l'avoir consignée — mais dans l'autre langage. J'ai
transposé la *forme* du test (« balayage + grand montant ») sans refaire la mesure qui lui
donnait son sens. Un test recopié depuis un autre contexte est une supposition déguisée en
vérification.

**Ce qui est vrai, et qui remplace le faux témoin.** En JavaScript, arithmétique entière
et `toFixed(2)` coïncident sur tout le domaine représentable. `Math.trunc` reste préférable
par cohérence avec l'invariant du projet, mais ce n'est pas une correction de bug — et le
prétendre trompait le prochain lecteur. Le test dit désormais ce qu'il vérifie vraiment :
l'exactitude jusqu'à la limite des entiers sûrs, et l'existence de cette limite.

**Généralisation.** La leçon d'une erreur ne se transporte pas d'un langage à l'autre par
la forme du test. Ce qui se transporte, c'est la question : *quelle implémentation fautive
ce test rejette-t-il ?* — et il faut la reposer à chaque fois, en l'exécutant.

---

## 015 — La liste des chemins d'API, écrite deux fois

**Zone** : `frontend/vite.config.ts`, `backend/mycounts/api/app.py`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que le proxy de développement était configuré une fois pour toutes.
Je l'avais écrit en énumérant les préfixes servis par l'API : `['/auth', '/health']`.

**Ce que j'ai mesuré.** Après avoir ajouté les routes du budget, l'écran restait bloqué
sur la page de connexion malgré une authentification à 200. La cause : `/comptes` renvoyait
le HTML de l'application au lieu du JSON. Le proxy ne connaissait pas ce chemin, et Vite,
faute de règle, servait l'`index.html` — donc une réponse **200 valide**, simplement pas
celle attendue.

**Pourquoi la faute était inévitable.** Cette liste était une seconde source de vérité en
face du routeur FastAPI. Rien ne les reliait : ajouter une route côté serveur ne pouvait
pas mettre à jour le proxy, et aucun test ne comparait les deux. C'est l'anti-pattern
n°3 — une donnée à deux auteurs — appliqué à de la configuration.

**Le contrôle qui a tranché.** Le corps de la réponse, pas son code. Un 200 qui renvoie du
HTML là où on attend du JSON est indiscernable d'un succès tant qu'on ne regarde que le
statut. Même famille que #004 (un skip ressemble à un pass) et #012 (un vert pour le
mauvais commit).

**Correction.** Un préfixe `/api` unique côté serveur, une seule entrée dans le proxy. La
liste disparaît, donc elle ne peut plus diverger. Corriger la liste aurait marché jusqu'à
la prochaine route.

**Généralisation.** Quand deux endroits doivent rester d'accord et que rien ne les y
oblige, ils finiront par ne plus l'être. La bonne réponse est rarement de les
resynchroniser : c'est de supprimer l'un des deux.

---

## 016 — Une sonde qui mesurait une page encore vide, seulement en CI

**Zone** : `frontend/e2e/contraste.spec.ts`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que `await expect(page.locator('nav')).toBeVisible()` garantissait que
l'écran était rendu avant de mesurer les contrastes. Les six tests passaient en local.

**Ce que j'ai mesuré.** La CI a fait échouer cinq d'entre eux sur le message
« aucun texte mesuré : la sonde est cassée ». La barre de navigation est rendue **à côté**
de l'écran, pas dedans : elle apparaît pendant que le contenu charge encore ses données.
En local, la base répond assez vite pour que la fenêtre soit invisible ; en CI, non.

**Pourquoi le test local ne pouvait pas le voir.** Il ne mesurait pas une propriété du
code mais une propriété de la latence de ma machine. Une même exécution, sur un poste plus
lent, aurait donné un autre résultat — c'est-à-dire que la mesure n'était pas
reproductible, donc pas une mesure.

**Ce qui a sauvé la situation.** L'assertion `expect(mesures.length).toBeGreaterThan(5)`,
écrite au moment de la sonde comme garde-fou contre elle-même. Sans elle, les six tests
auraient été **verts sur une page vide** : aucun texte à mesurer, donc aucun texte sous le
seuil. Un contrôle de contraste qui ne mesure rien passe toujours.

**Correction.** Attendre le contenu (`main` et au moins un élément dedans), pas la
navigation.

**Généralisation.** Deux leçons distinctes. La première : un test qui dépend d'une course
entre le rendu et la mesure ne teste pas ce qu'il annonce. La seconde, plus utile : tout
contrôle qui parcourt une collection doit vérifier qu'elle n'est pas vide — c'est la
troisième fois que ce garde-fou paie, après #005 et #013.

---

## 017 — Un témoin qui testait le code d'avant

**Zone** : méthode de vérification des témoins backend via Playwright.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Qu'en retirant la protection « refuser la suppression d'une catégorie
utilisée » puis en relançant le test de bout en bout, je vérifiais que ce test la détecte.
Il est passé au vert. J'ai failli en conclure que le témoin ne prouvait rien et récrire
un test qui n'avait aucun problème.

**Ce que j'ai mesuré.** Playwright est configuré avec `reuseExistingServer: true`, et
uvicorn tourne **sans rechargement automatique**. Le serveur en mémoire exécutait donc
toujours l'ancien code, protection incluse. Ma modification du fichier n'avait aucun effet
sur ce qui répondait aux requêtes. Après redémarrage d'uvicorn, le test échoue comme
attendu, et repasse au vert une fois la protection remise.

**Pourquoi c'est la même erreur qu'avant.** Troisième variante de « la mesure porte sur le
mauvais sujet », après #007 (le mauvais port, donc la mauvaise application) et #012 (le
mauvais commit). Ici, c'est le mauvais **état du serveur** : le fichier sur le disque et le
processus qui répond avaient divergé.

**Ce que ça aurait coûté.** Le pire scénario n'était pas de perdre du temps : c'était de
conclure qu'un bon test est inutile et de l'affaiblir. Un témoin déclaré inefficace à tort
est supprimé, et la protection qu'il gardait s'en va au commit suivant.

**Méthode corrigée.** Tout témoin qui modifie du code **serveur** exige un redémarrage
d'uvicorn avant le test, et une vérification que le fichier est bien restauré après
(`grep` sur la ligne retirée). Les témoins frontend, eux, profitent du rechargement à
chaud de Vite et n'ont pas ce problème.

**Incident annexe, du même tour.** Un `cd frontend` en milieu de commande a fait échouer
la restauration du fichier : le `cp` de retour s'est exécuté depuis le mauvais répertoire
et a silencieusement échoué. Le code est resté amputé de sa protection le temps de le
remarquer. Vérifier la restauration, toujours — ne pas la supposer.

---

## 018 — Un trou entre l'agenda et les opérations

**Zone** : `backend/mycounts/api/agenda.py`, `backend/mycounts/api/budget.py`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que l'agenda (échéances à venir) et la liste des opérations
(échéances passées, matérialisées) couvraient ensemble toute la ligne du temps. L'agenda
commence à aujourd'hui, les opérations s'arrêtent à ce qui existe : les deux se touchent,
donc rien ne manque.

**Ce que j'ai mesuré.** Un test attendait qu'une échéance datée d'hier disparaisse de
l'agenda après matérialisation. Il a échoué avec `2 == 1` : elle n'y avait **jamais**
figuré. L'agenda démarrant à aujourd'hui, une échéance d'hier n'y est pas — et tant que le
job n'a pas tourné, elle n'est pas non plus une opération. Elle n'apparaît nulle part.

**Pourquoi le raisonnement était faux.** Les deux vues ne se touchent pas : elles se
recouvrent sur ce qui est *déjà matérialisé*, et laissent un trou sur ce qui est *échu mais
pas encore traité*. La taille du trou dépend du délai entre l'échéance et le passage du
job — c'est-à-dire d'un ordonnanceur qui n'existe pas encore. Sur une application d'argent,
c'est la pire forme de défaut : de l'argent absent de tous les écrans, puis qui réapparaît.

**Le contrôle qui a tranché — et qui est maintenant en place.** Un test qui ne lance
**aucun** job et vérifie que la seule lecture de l'agenda fait remonter l'échéance d'hier.
Il échouerait si le rattrapage disparaissait.

**Correction.** La lecture de l'agenda et du résumé matérialise au passage. Un effet de
bord sur un GET se discute — ici il est **idempotent** (clé d'unicité en base) et il ferme
un trou réel. L'alternative propre, un ordonnanceur, viendra au lot de déploiement ; d'ici
là, mieux vaut un GET qui rattrape qu'un écran qui ment.

**Généralisation.** Deux vues « complémentaires » ne couvrent pas forcément tout : la
question n'est pas « chacune est-elle juste ? » mais « **existe-t-il un état que ni l'une
ni l'autre ne montre ?** ». Même forme que #010, où une opération tombait entre quatre
agrégats tous corrects isolément.

---

## 019 — Une CI bloquée quarante minutes sur une option d'installation

**Zone** : `Makefile`, cible `front-installer`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Que `npx playwright install --with-deps chromium` était la commande
recommandée pour la CI — c'est celle que la documentation met en avant — et qu'elle
coûterait quelques dizaines de secondes.

**Ce que j'ai mesuré.** Deux exécutions bloquées : l'étape « Installer le frontend » est
restée `in_progress` pendant plus de quarante minutes, sans erreur ni sortie. Les étapes
précédentes étaient toutes vertes ; les suivantes, en attente. `--with-deps` déclenche un
`apt-get install` système qui n'a jamais rendu la main sur le runner.

**Pourquoi je ne l'ai pas vu plus tôt.** Ma nouvelle cadence — pousser sans attendre la
CI — est bonne, mais elle déplace la détection au tour suivant. Entre-temps, un second
commit s'est empilé derrière le premier, bloqué de la même façon. Un blocage silencieux
est plus long à voir qu'un échec : rien ne rougit, la file grossit simplement.

**Le contrôle qui a tranché.** Lire les **étapes** du job (`gh api …/jobs`), et non son
statut global. « En cours » ne dit pas *où*.

**Correction.** `playwright install chromium` sans `--with-deps` : les bibliothèques dont
Chromium a besoin sont déjà présentes sur `ubuntu-latest`. Les navigateurs sont par
ailleurs mis en cache depuis le commit précédent.

**Généralisation.** Ne plus attendre la CI ne dispense pas de regarder si elle **avance**.
Un job qui ne finit jamais ne produit aucun signal rouge — il faut donc contrôler la durée,
pas seulement la conclusion.

---

## 020 — La classe « Verre » a écrasé son hôte une seconde fois

**Zone** : `frontend/src/composants/Verre.module.css`, `BarreOnglets.module.css`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Qu'après avoir retiré `position` de la classe `.verre` (ERREURS.md
#008), elle était devenue sûre à combiner : elle ne déclarait plus que du matériau, pas
de la mise en page.

**Ce que j'ai mesuré.** En retirant le fond du rail au format bureau (`background: none`
dans une media query), le panneau bleu est resté à l'écran. Même spécificité, feuille
`Verre` chargée après : c'est elle qui gagnait, exactement comme la première fois. La
capture d'écran l'a montré, pas un test.

**Pourquoi la première correction n'a pas suffi.** J'avais traité le symptôme —
`position` — sans voir la propriété du problème : **toute** déclaration d'une classe
utilitaire est une décision retirée à son consommateur. `background` et `backdrop-filter`
sont tout aussi structurants que `position` dès lors qu'un écran veut les contredire selon
la taille de la fenêtre.

**Correction.** La barre de navigation porte désormais son propre verre, écrit dans son
module, et le retire elle-même au format bureau. La classe utilitaire n'est plus appliquée
de l'extérieur sur un élément dont la mise en page varie.

**Généralisation.** Une classe utilitaire n'est combinable sans risque que si son
consommateur n'a jamais besoin de contredire ce qu'elle déclare. Quand ce besoin existe,
la solution n'est pas d'augmenter la spécificité : c'est de déplacer la déclaration chez
celui qui décide. Deuxième occurrence — la première correction avait traité le cas, pas
la cause.

---

## 021 — Ma sonde de contraste, trompée une troisième fois

**Zone** : `frontend/e2e/contraste.spec.ts`.
**Date** : 2026-08-19.

**Ce que j'ai cru.** Qu'après avoir corrigé la lecture de `color(srgb …)` (#011), la sonde
lisait correctement le fond de n'importe quel élément.

**Ce que j'ai mesuré.** En passant les boutons à un dégradé, elle a annoncé **1,02:1** sur
« Saisir une dépense » — un bouton violet à texte blanc, parfaitement lisible.
`getComputedStyle().backgroundColor` vaut `rgba(0,0,0,0)` quand le fond est un
`linear-gradient` : la sonde remontait alors au parent et concluait « blanc sur blanc ».

**La deuxième erreur, dans ma correction.** J'ai d'abord extrait les arrêts du dégradé et
retenu le **pire rapport parmi tous les candidats**, fond composé inclus. Résultat
inchangé : 1,02. Le fond composé étant faux quand un dégradé le recouvre, et la règle du
pire cas retenant systématiquement le plus mauvais, mon candidat erroné gagnait toujours.
*Un candidat faux n'est pas un pire cas, c'est du bruit.* Quand un dégradé est présent, ce
sont ses arrêts, et eux seuls, qui font foi.

**Ce que la sonde corrigée a alors trouvé.** Un vrai défaut : mon dégradé partait de
`#7A73FF` en haut, plus clair que le primaire, ce qui donnait **3,67:1** — sous le seuil.
L'arrêt le plus clair a été ramené au primaire lui-même, dont les 4,68:1 constituent déjà
la limite basse.

**Généralisation.** Une sonde qui mesure le monde à travers une API a un domaine de
validité, et il faut le connaître : `backgroundColor` ne décrit qu'une couleur unie. Trois
fois de suite, ce sont ses angles morts qui m'ont trompé — jamais le code mesuré. Et une
règle d'agrégation comme « prendre le pire » n'est saine que si tous les candidats sont
valides.

## #022 — J'ai livré une interface à jour posée sur une API figée, deux fois

**Ce que je croyais.** Que la démonstration servait le code que je venais d'écrire.
J'avais vérifié à l'écran que le détail d'une opération s'affichait, et j'en avais conclu
que la suppression marchait. Olivier a cliqué sur Supprimer : « Not Found ».

**Ce que j'ai mesuré.** Le schéma OpenAPI du serveur de démonstration ne contenait ni
`DELETE` ni `PATCH /api/operations/{id}`. Vite recharge le frontend à chaud, uvicorn non :
l'écran était à jour, l'API datait d'avant la fonctionnalité.

**Pourquoi ma mesure ne prouvait rien.** J'avais vérifié la seule moitié qui se recharge
toute seule. Un affichage correct ne dit rien de la route qu'il appelle : c'est
exactement #017, que j'avais déjà écrite, et que j'ai refaite.

**Et une seconde cause dessous.** Après redémarrage, la suppression rendait 500 :
`column operation.annulee does not exist`. J'avais migré la base de développement, pas
celle de la démonstration. L'application avait démarré sans broncher sur un schéma
incompatible et n'a échoué qu'à la première requête touchant la colonne — un message
opaque, très loin de sa cause.

**Le contrôle qui aurait tranché.** Ne pas dépendre de ma rigueur. L'API vérifie
maintenant au démarrage que la révision de la base est la tête Alembic, et **refuse de
démarrer** sinon, en nommant la commande à lancer. Témoin dans
`tests/integration/test_garde_migrations.py`, vérifié par mutation : garde-fou neutralisé,
le test rougit. `make demo` gagne `--reload` pour la moitié qui manquait.

## #023 — Mon témoin ne testait rien : un raccourci CSS écrasait la mutation

**Ce que je croyais.** Qu'un garde-fou tout neuf sur la hauteur des modales était aveugle.
Je lui avais opposé une feuille regonflée de 120 px, puis de 300 px : vert les deux fois.
J'ai commencé à soupçonner ma sonde.

**Ce que j'ai mesuré.** `getComputedStyle(feuille).paddingTop` valait `16px`. La mutation
n'avait jamais atteint la page : je l'insérais en TÊTE de la règle, où le raccourci
`padding: var(--espace-l)` écrit trois lignes plus bas l'écrasait intégralement.

**Pourquoi ma mesure ne prouvait rien.** Elle ne portait pas sur le sujet que je croyais.
Le test voyait une feuille intacte et la déclarait conforme — ce qu'elle était. Sixième
entrée de cette famille sur vingt-trois, et la plus sournoise : ici le mauvais sujet
n'était ni une machine, ni un port, ni un commit, mais une déclaration CSS silencieusement
annulée par une autre.

**Le contrôle qui aurait tranché.** Avoir lu la valeur EFFECTIVE dans le navigateur avant
de conclure quoi que ce soit sur le test — un seul `getComputedStyle`, trente secondes.
Vérifier que le fichier contient la mutation ne prouve rien : j'avais bien vérifié, et
compté une occurrence. Le fichier la contenait ; la page, non. Reposée en fin de règle,
la mutation a fait rougir le test sur-le-champ, en nommant « Supprimer » et
« Enregistrer » comme hors écran.

## #024 — J'ai conclu « réglé » depuis une seule largeur d'écran

**Ce que je croyais.** Qu'empiler montant et date sous 400 px réglait le champ de date
coupé par le bord de l'écran sur iPhone. Mon garde-fou passait au vert et je l'ai annoncé.

**Ce que j'ai mesuré.** Une seule largeur : 390 px. L'appareil d'Olivier en fait **430**.
Au-dessus de mon seuil, donc en deux colonnes, donc le défaut intact — sa seconde capture
était identique à la première.

**Pourquoi ma mesure ne prouvait rien.** Une mise en page qui tient à une largeur ne dit
rien de la suivante, et c'est précisément à la largeur non testée que vivait le défaut.
J'avais choisi 390 px comme « le téléphone », alors que c'est une famille de tailles. La
même faute que #016 et #007 sous un autre déguisement : la mesure portait sur un sujet
voisin de celui qui m'intéressait.

**Ce que je n'ai toujours pas.** Aucun moteur local ne rend le widget de date d'iOS —
Chromium, WebKit de bureau et l'émulation iPhone de Playwright le déclaraient tous les
trois conforme. Je ne peux donc pas *observer* ce défaut, seulement supprimer la condition
qui le rend possible. D'où le choix d'empiler sur toute largeur de téléphone plutôt que de
chercher la valeur qui ferait tenir deux colonnes : je n'ai aucun moyen de vérifier une
telle valeur.

**Le contrôle qui aurait tranché.** Le garde-fou tourne désormais sur deux largeurs, 390
et 430. Il ne détecterait toujours pas ce défaut-ci — il est propre à un moteur absent de
ma machine — mais il détecte la classe de fautes que je viens de commettre : conclure
d'une largeur à toutes les autres.

## #025 — J'ai corrigé deux fois avant d'avoir diagnostiqué

**Ce que je croyais.** Que le champ de date coupé par le bord de l'écran était un problème
de partage de largeur. J'ai empilé les champs sous 400 px. Échec. J'ai monté le seuil à
600 px. Échec encore. Trois allers-retours avec Olivier pour un seul défaut.

**Ce que j'ai mesuré — trop tard.** Les positions dans sa capture. La feuille laisse 398 px
utiles, le champ Libellé en occupe 398, le champ de date 432. Soit exactement
`398 + 2 × 16 de padding + 2 × 1 de bordure` : iOS ignore `box-sizing: border-box` sur
`input[type="date"]`. Le calcul tombait juste au pixel près, et **la première capture
contenait déjà tout ce qu'il fallait pour le faire**.

**Pourquoi mes deux premières corrections ne prouvaient rien.** Elles traitaient une cause
supposée. Le défaut ne dépendait ni de la largeur partagée ni du seuil : il était constant,
18 px, à toute largeur. Aucune de mes deux tentatives ne pouvait le déplacer — j'aurais pu
le savoir avant de les livrer.

**Le contrôle qui aurait tranché.** Mesurer avant de corriger, y compris quand la seule
donnée disponible est une image. Les bords visibles d'une capture sont des nombres : le
champ Libellé s'y arrêtait net à la bonne largeur, le champ de date non — deux quantités
qui devaient être égales et ne l'étaient pas. C'était la mesure à faire, et elle ne
demandait aucun appareil.

## #026 — J'ai reformaté des fichiers avec un outil qui n'est pas celui du projet

**Ce que je croyais.** Que lancer `prettier` après une modification était neutre.

**Ce que j'ai mesuré.** Le dépôt n'a **aucune configuration prettier** : son linter est
`oxlint`, et le style maison est guillemets simples, sans point-virgule, 100 colonnes.
Prettier sans configuration applique ses propres valeurs par défaut — guillemets doubles,
points-virgules. J'ai donc reformaté silencieusement `FeuilleOperation.tsx`,
`contraste.spec.ts` et `tokens.ts`, et livré ces changements dans des commits dont le
message ne parlait que de mise en page ou de contraste.

**Pourquoi ma mesure ne prouvait rien.** Je n'en avais fait aucune. J'ai supposé qu'un
formateur répandu était le formateur DE CE dépôt. Aucun garde-fou ne pouvait me
contredire : le style n'est pas vérifié en CI, donc tout restait vert.

**Le contrôle qui aurait tranché.** Compter les points-virgules d'un fichier que je
n'avais pas touché — trois secondes, réponse sans ambiguïté : zéro. C'est ce que j'ai fini
par faire, après trois commits. Le style est maintenant écrit dans `frontend/.prettierrc`,
pour que la question ne se repose plus à celui qui lancera l'outil.

## #027 — Deux fautes de requête qui rendaient des chiffres d'argent faux

**Ce que je croyais.** Que filtrer les comptes d'épargne en Python était équivalent à le
faire en SQL, et qu'une clause `where` suffisait à joindre deux tables.

**Ce que j'ai mesuré.** Deux échecs successifs du même test, avec deux causes distinctes.

D'abord une épargne à **zéro** alors que le livret contenait 500 €. La colonne
`type_compte` est un `String(16)` : SQLAlchemy rend une chaîne, pas un membre de
`TypeCompte`. Mon `compte.type_compte is not TypeCompte.EPARGNE` était donc vrai pour
TOUS les comptes — l'identité échoue là où l'égalité aurait réussi, `StrEnum` comparant
bien à sa valeur. Aucune erreur, aucun type refusé : juste une boucle qui ne garde rien.

Puis un « versé sur la période » de **400 € pour un virement de 200**. Ma requête
d'agrégat référençait `Compte` dans son `where` sans jointure : PostgreSQL a ajouté la
table au `FROM` en produit cartésien, et la somme s'est trouvée multipliée par le nombre
de comptes du foyer.

**Pourquoi ces fautes sont sournoises.** Aucune ne lève. La première rend zéro, la
seconde un multiple — deux résultats parfaitement plausibles à la lecture. Sur un écran
d'épargne, « vous avez versé 400 € ce mois-ci » ne se conteste pas de tête.

**Le contrôle qui a tranché.** Le test portait sur des montants CHOISIS pour se
distinguer : 500 € d'ouverture, 200 € virés, deux comptes. Un test à un seul compte
n'aurait pas vu le facteur deux ; un test à montants égaux n'aurait pas vu lequel des
deux était compté. C'est le choix des nombres qui a fait parler la mesure, pas sa
présence.

## #028 — Un script promettait un état qu'il ne produisait pas

**Ce que je croyais.** Que la remise à zéro du foyer d'essai laissait « un compte, aucune
opération, aucune récurrence » — c'est ce qu'annonce la première ligne du fichier.

**Ce que j'ai mesuré.** La page Épargne affichait quatre livrets là où le test venait d'en
créer un. Deux d'entre eux dataient de l'exécution PRÉCÉDENTE : le script supprimait les
opérations et les récurrences, jamais les comptes.

**Pourquoi l'écart est resté invisible si longtemps.** Aucun test ne créait de second
compte. L'en-tête était donc vrai par accident, et le premier test à en créer un l'a mis
en défaut. Un état « garanti » que rien ne vérifie n'est pas garanti, c'est une intention
— exactement ce que `CLAUDE.md` dit d'une ligne sans fichier derrière elle.

**Un effet de bord instructif.** Les comptes accumulés ont fait apparaître un sélecteur de
compte dans la feuille des prélèvements, qui ne s'affiche qu'au-delà d'un compte — et
cette feuille a cessé de tenir dans l'écran. Le garde-fou des modales a rougi pour une
cause située à trois fichiers de là. Ce n'était pas un faux positif : dès qu'un foyer
ouvre une épargne, il a deux comptes, et la feuille débordait pour de bon.

**Le contrôle qui aurait tranché.** `tests/integration/test_reinitialisation.py` crée
trois comptes, lance le script, et compte ce qui reste. Le témoin part de trois pour que
« il en reste un » ne puisse pas être vrai par hasard.

## #029 — J'ai changé une couleur de la DA sans le dire assez fort

**Ce que je croyais.** Qu'annoncer « j'ai éclairci le rouge des débits » au milieu d'un
compte rendu suffisait à faire valider le changement. La ligne y était, chiffrée.

**Ce qu'il s'est passé.** Olivier l'a découvert sur une capture, plusieurs échanges plus
tard : « pourquoi t'as changé les couleurs ? ». Il a demandé le retour à la palette
d'origine, et il a eu raison de la demander — c'est sa direction artistique, pas la mienne.

**Pourquoi mon annonce ne valait pas accord.** Une couleur de la DA n'est pas un détail
d'implémentation qu'on corrige en passant parce qu'une mesure l'exige. La mesure dit ce
qui est vrai ; elle ne dit pas quel arbitrage rendre entre lisibilité et identité. J'avais
noyé une décision qui lui appartenait dans un compte rendu de six paragraphes.

**Ce que j'aurais dû faire.** Poser la question AVANT de changer, avec les trois options
et leurs chiffres — ce que j'ai fini par faire, mais après coup. Le coût d'une question
est d'un aller-retour ; celui d'un changement non validé, de trois.

**Le contrôle en place maintenant.** La palette d'origine est rétablie et le rouge des
débits porte une dérogation BORNÉE dans `e2e/contraste.spec.ts` : son seuil est abaissé à
la valeur mesurée (3,2 au lieu de 4,5), pas supprimé. Vérifié par mutation — halo poussé
à 0,42, les trois tests du thème sombre rougissent. La dérogation couvre une décision
prise, elle ne couvre pas une dégradation future.

## #030 — Une alerte documentée qui ne pouvait pas se déclencher

**Ce que je croyais.** Que `depasse_avec_les_echeances` fonctionnait : le domaine le
calcule, `docs/PLAN.md` le décrit comme « le vrai signal », et onze tests d'intégration
passaient sur les plafonds.

**Ce que j'ai mesuré.** En construisant l'écran, l'alerte ne s'affichait jamais. `a_venir`
ne compte que les opérations à l'état `prevue` — et **rien, nulle part, n'en crée**. La
matérialisation n'écrit une ligne qu'une fois l'échéance échue : le futur n'est dans
aucune table, c'est une projection calculée à la volée par l'agenda. `a_venir` valait donc
zéro depuis toujours, et `depasse_avec_les_echeances` n'était qu'un synonyme de `depasse`.

**Pourquoi les tests ne l'ont pas vu.** Ceux du domaine fabriquaient les opérations
`prevue` à la main. Ils prouvaient que la FONCTION calcule juste — ce qui était vrai — et
non que le système lui fournit jamais cette entrée. Un test unitaire qui construit son
entrée ne peut pas révéler qu'aucun producteur ne l'écrit.

**Le contrôle qui aurait tranché.** Un test d'intégration qui part d'une RÉCURRENCE, comme
l'utilisateur : créer un prélèvement dans une catégorie plafonnée, puis lire l'API. Il
existe maintenant, et il vérifie deux grandeurs qui ne bougent pas ensemble — l'à-venir
monte pendant que le consommé reste ce qui est réellement sorti. Vérifié par mutation :
projection débranchée, il rougit.

**Corrigé** en extrayant la projection des échéances dans le dépôt, partagée par l'agenda
et les plafonds. Deux copies auraient fini par diverger.

## #031 — Un effet qui existait dans le code et nulle part à l'écran

**Ce que je croyais.** Que la transition d'élément partagé fonctionnait : le code FLIP
était écrit, les types passaient, les tests restaient verts.

**Ce que j'ai mesuré.** L'avatar partait de sa position d'ARRIVÉE, à 198 px de la bulle.
En listant `getAnimations()` sur l'élément : **deux** animations. La première juste —
`translate(-181px, -80px) scale(0.52)`, exactement l'écart vers la bulle. La seconde nulle
— `translate(0, 0) scale(1)`. React en mode strict rejoue l'effet ; le second passage
mesurait une position DÉJÀ DÉPLACÉE par le premier, calculait donc un trajet nul, et
l'emportait en étant joué en dernier.

**Pourquoi rien ne m'a alerté.** Aucun test ne regardait le mouvement. Un effet visuel qui
ne casse rien passe tous les contrôles d'un projet qui n'en mesure aucun — et en
production, sans mode strict, il aurait fonctionné. J'aurais livré un effet dont je ne
savais pas s'il tenait.

**Le contrôle qui a tranché.** Lire la première image de position de l'élément et la
comparer au centre de la bulle : deux nombres, un écart, une réponse. Corrigé en annulant
toute animation en cours sur l'élément AVANT de mesurer.

**Une seconde mesure, imprévue.** Le débit tombait de 61 à **36 images par seconde** :
un `backdrop-filter` plein écran refait son flou à chaque image tant que ce qu'il recouvre
bouge — et les halos voyagent. Figer les halos pendant qu'un écran les recouvre l'a
ramené à 55. Sans mesure, l'effet aurait été livré saccadé sur téléphone.

## #032 — Un module CSS renomme aussi les noms d'animation

**Ce que je croyais.** Qu'il suffisait de déplacer des `@keyframes` dans `global.css` pour
les partager entre plusieurs modules. Le code compilait, les types passaient, la suite
restait verte.

**Ce que j'ai mesuré.** `getAnimations()` sur la sous-page : **tableau vide**. Aucune
animation ne jouait. Un module CSS ne renomme pas seulement ses classes : il renomme aussi
les `animation-name` qu'il rencontre. Mes modules pointaient donc vers un nom qui n'existe
nulle part, et le navigateur ignorait la déclaration en silence — ni erreur, ni
avertissement, ni style visiblement cassé.

**Pourquoi rien ne l'a vu.** Olivier, lui, l'a vu tout de suite : « pour l'ouverture des
sous-menus il doit y avoir le motion ». Aucun test ne regardait si une animation existait,
et une animation absente ne casse rien — elle rend seulement l'interface plus pauvre, ce
qu'aucun contrôle du projet ne mesurait.

**Une seconde faute, indépendante et mesurable.** Le panneau animait `clip-path`, que le
compositeur ne sait pas jouer : chaque image forçait une repeinte plein écran, sous un
verre qui refaisait son flou. **33,3 ms par image, soit trente par seconde.** Passé à
`scale` et `opacity`, et le verre suspendu le temps du mouvement : **16,7 ms**, soit
soixante.

**Le contrôle en place.** `e2e/mouvement.spec.ts` vérifie que chaque écran anime QUELQUE
CHOSE, et que ce quelque chose fait partie des propriétés que le compositeur joue sans
repeindre. Il ne chronomètre rien — une mesure de temps serait instable en intégration
continue — il vérifie les deux causes, qui elles sont déterministes. Vérifié par mutation
sur chacune.

## #033 — Des localisateurs uniques le jour où je les écris, ambigus le lendemain

**Ce que je croyais.** Que `getByRole('button', { name: 'Virement' })` désignait le bouton
de la feuille de saisie. C'était vrai quand je l'ai écrit.

**Ce que j'ai mesuré.** Neuf correspondances. Les virements créés par les tests portent le
libellé « Virement », et chaque ligne d'opération de l'accueil est un bouton nommé
« Détail de Virement ». Même histoire pour « Retour », rendu ambigu par un compte d'essai
que j'avais nommé « Livret retour ».

**Pourquoi ça ne pouvait qu'arriver.** Les tests partagent une base qui se remplit au fil
de la suite. Un localisateur par sous-chaîne est unique tant que les données sont pauvres
et cesse de l'être dès qu'elles ressemblent à de vraies données — c'est-à-dire au moment
précis où la suite devient utile. Le défaut n'est pas dans le test qui échoue, il est dans
tous ceux qui ont été écrits pareil.

**Le contrôle en place.** `exact: true` sur tous les libellés d'action courts — Retour,
Fermer, Virement, Dépense, Revenu, Enregistrer, Supprimer, Confirmer, Annuler — et les
cartes cadrées sur leur panneau plutôt que cherchées dans la page entière. Huit fichiers
corrigés d'un coup, parce que corriger seulement celui qui rougissait aurait laissé les
sept autres attendre leur tour.

## #034 — Un contrôle vert qui n'avait jamais rien vérifié

**Ce que je croyais.** Que `make front-lint` typait le frontend. Il tourne depuis le début
du projet, il est appelé par `make verifier`, il est vert, et sa ligne dit
`npx tsc --noEmit`.

**Ce qu'il s'est passé.** Il ne compilait aucun fichier. Le `tsconfig.json` racine est un
fichier de RÉFÉRENCES — `"files": []` plus deux `references`. Sans `-p`, `tsc` prend ce
fichier, n'y trouve aucun fichier à compiler, affiche « No errors found » et sort en 0.
Toujours. Quelle que soit l'erreur présente dans le code.

**Comment je l'ai vu.** Par accident, en lançant `tsc --noEmit -p tsconfig.app.json` pour
vérifier mon propre travail : il a trouvé une erreur de type réelle dans `Enveloppes.tsx`,
présente dans l'arbre de travail depuis la veille, que `make front-lint` déclarait saine.
Les deux formes ont alors été exécutées côte à côte sur le même code : sortie 0 pour l'une,
sortie 2 pour l'autre.

**Pourquoi je ne l'avais pas vu plus tôt.** Parce qu'un garde-fou vert ne demande rien à
personne. Le projet exige que chaque témoin soit vérifié par mutation — casser
l'implémentation, voir le test rougir — et cette règle n'avait jamais été appliquée aux
outils du `Makefile` eux-mêmes. Un contrôle qui ne peut pas rendre la réponse « rouge »
n'est pas un contrôle, et c'est vrai d'un `tsc` comme d'un test.

**Le contrôle en place maintenant.** `front-lint` appelle `-p` sur chacun des deux projets,
et le `Makefile` porte en commentaire la raison exacte, avec la date de la mesure. La
vérification par mutation vaut désormais pour les cibles du `Makefile` autant que pour les
tests : avant de croire un contrôle, lui présenter la faute qu'il prétend détecter.

## #035 — Le contraste mesuré sur un aplat, la couleur posée sur un halo

**Ce que je croyais.** Qu'en changeant la palette pour du bleu ardoise, le rouge des débits
`#FB7185` n'avait plus besoin de sa dérogation : je l'avais mesuré à 6,63:1 sur le fond
`#0F172A`, très au-dessus du seuil de 4,5. J'ai retiré la dérogation et je l'ai annoncé
comme un gain.

**Ce qu'il s'est passé.** La sonde `e2e/contraste.spec.ts` a rendu 3,51:1 sur les centimes
des montants. Elle avait raison et mon calcul avait tort : un montant n'est jamais posé sur
le fond nu. Le halo passe dessous et l'éclaircit fortement, et c'est ce fond composite qui
décide du contraste. J'avais mesuré une couleur sur une autre couleur ; l'écran, lui,
empile un fond, un halo, une surface de verre et un texte.

**La faute de fond.** C'est la cinquième fois dans ce fichier que la mesure porte sur le
mauvais sujet, et la troisième pour le contraste précisément — après #011 et #021. La règle
existait déjà, écrite dans `CLAUDE.md` : *une sonde a un domaine de validité, le connaître
avant de croire son verdict*. Un calcul de contraste sur deux valeurs hexadécimales a pour
domaine de validité « deux aplats opaques superposés ». Ce n'est pas la situation de cette
interface, qui est faite de couches translucides — c'est même exactement ce que la DA
Liquid Glass rend impossible à calculer de tête.

**Ce que ça a failli coûter.** Une dérogation retirée à tort aurait laissé passer, sans
plus aucun garde-fou, la dégradation qu'elle existait pour surveiller.

**Le contrôle en place maintenant.** La dérogation est rétablie, plancher à 3,5 — la valeur
mesurée par la sonde, pas par moi. Et la règle est explicite dans `tokens.ts` : le chiffre
qui fait foi est celui du rendu, jamais celui d'un aplat. Quand les deux divergent, c'est
le calcul sur aplat qui parle d'autre chose.

## #036 — Une sonde qui ne pouvait rien voir sur un foyer vide

**Ce que je croyais.** Que `contraste.spec.ts` couvrait la palette, puisqu'il parcourt tous
les textes visibles de l'accueil dans deux thèmes et trois positions de transparence.

**Ce qu'il s'est passé.** Lancé seul, il passait. Lancé dans la suite complète, il
échouait — sur quarante-deux textes. J'ai d'abord lu ça comme une interférence entre
tests, c'est-à-dire comme un défaut de la suite. C'était l'inverse : le foyer d'essai est
réinitialisé VIDE, une page sans opération n'affiche aucun montant, donc ni vert ni rouge —
et ce sont précisément les deux couleurs les plus difficiles à faire passer. Seule la suite
complète, en laissant des données derrière elle, donnait à la sonde quelque chose à voir.

**Ce que ça dit.** La mesure isolée était la mesure aveugle. Un test dont le résultat dépend
de ce que d'autres tests ont laissé en base ne prouve rien, ni quand il rougit ni quand il
passe.

**Le contrôle en place maintenant.** Le fichier crée lui-même un débit et un crédit avant de
mesurer (`garantirDesMontants`). Il ne dépend plus de l'ordre d'exécution et reproduit le
défaut seul, de façon déterministe.

## #037 — Une constante placée avant l'état qu'elle lit

**Ce que je croyais.** Qu'ajouter `const laCategorieDitLaPaie = …` juste sous `const sortie`
était sans risque : `tsc` passait, le lint passait, la vérification des classes CSS passait.

**Ce qu'il s'est passé.** La constante lisait `categorieId`, déclaré vingt lignes plus bas
par `useState`. Zone morte temporelle : `ReferenceError: Cannot access 'categorieId' before
initialization`, et la feuille de saisie qui plante entièrement.

**Pourquoi rien ne l'a vu.** TypeScript ne signale pas toutes les TDZ, et surtout le bogue
était MASQUÉ par un court-circuit : la constante s'écrit `!sortie && categories.find(…)`, si
bien qu'en mode Dépense — le mode testé partout — l'expression s'arrêtait avant de toucher à
`categorieId`. Seuls les modes Revenu et Virement plantaient. Le parcours de saisie passait
au vert pendant que l'écran était cassé pour deux de ses trois modes.

**Ce que ça dit.** Un court-circuit booléen peut cacher une erreur d'initialisation dans la
branche non prise, et la branche non prise est souvent celle qu'on teste le moins. Le
défaut n'est apparu que dans le test d'épargne, qui fait un virement.

**Le contrôle en place maintenant.** La constante est déclarée après le `useState` qu'elle
lit. Aucun garde-fou automatique n'a été ajouté : ce qui l'a trouvé est un test de bout en
bout qui exerce un mode PEU fréquent, et c'est cette couverture-là qui vaut d'être
entretenue.

## #038 — Deux nombres choisis dans deux fichiers, un formulaire invisible

**Ce que je croyais.** Rien de particulier : les `z-index` étaient posés au fil de l'eau,
chacun dans le module qui en avait besoin.

**Ce qu'il s'est passé.** Olivier l'a signalé depuis son téléphone : ouvrir le formulaire de
prélèvement depuis le calendrier ne montrait rien. « Ça fait comme si rien s'affichait, on
est obligé de fermer l'écran calendrier. » Le formulaire était bien monté, bien focalisable,
il recevait la frappe — et il s'affichait DERRIÈRE l'écran qui l'avait ouvert. Les écrans
poussés étaient au plan 30, les feuilles modales au plan 20.

**Ce qui rend ce défaut typique.** Aucun des deux nombres n'était faux en lui-même. Ils
avaient été choisis dans deux fichiers différents, à deux moments différents, sans que
personne ne tienne la liste — et le défaut ne se voit que sur la combinaison des deux. Le
même trou touchait les Paramètres et le Détail d'épargne, jamais remarqué faute d'y ouvrir
une feuille.

**Le contrôle en place maintenant.** `tokens.ts` porte une échelle de plans nommés — `fond`,
`poignee`, `navigation`, `bulle`, `ecran`, `feuille`, `confirmation` — et plus aucun module
n'écrit de nombre. Un composant choisit un RÔLE, et l'ordre se lit à un seul endroit.

## #039 — Une consigne que je relisais, et que j'ai payée quand même

**Ce que je croyais.** Que `make migrer` suffisait après avoir écrit une migration.

**Ce qu'il s'est passé.** Olivier : « l'appli sert juste le background, là ça ne m'affiche
plus rien. » L'API de démonstration refusait de démarrer :

    BaseNonMigree: La base est en révision '9af113325c74', le code attend 'efe3ce18d323'.

Le lot C avait ajouté une migration. Je l'avais appliquée à la base de développement — d'où
des tests d'intégration verts, une suite de bout en bout verte, et une application morte
chez lui.

**Ce qui rend cette erreur particulière.** Elle était écrite. Noir sur blanc, dans
`BOUCLE.md`, dans la liste intitulée « pièges déjà payés, à ne pas repayer » : *la base de
DÉMONSTRATION se migre séparément (`make demo-migrer`). L'API refuse désormais de démarrer
si elle est en retard.* Je l'ai lue au début de la session, je l'ai eue sous les yeux à
chaque relecture du fichier, et je ne l'ai pas appliquée.

**La leçon, et elle vaut au-delà de ce cas.** Une consigne qu'on relit ne remplace pas un
contrôle qui la vérifie. Ce projet le sait déjà pour le code — c'est la raison d'être de ses
dix garde-fous — mais avait laissé cette règle-ci à l'état de phrase. Une phrase ne peut pas
rendre la réponse « rouge ».

Deux détails aggravants, tous deux du même genre : **rien de ce que je lance ne touche à la
base de démonstration**, donc aucune de mes vérifications ne pouvait voir le problème ; et
la vérification que je répétais à chaque lot était complète sur le mauvais périmètre. C'est
la sixième entrée de ce fichier où la mesure porte sur le bon sujet mais pas sur la bonne
machine.

**Le contrôle en place maintenant.** Garde-fou nº 11,
`scripts/verifier_demo_migree.py`, appelé par `make verifier`. Il AVERTIT sans bloquer —
une base de démonstration absente ou injoignable n'est pas une faute, et faire échouer la
vérification d'un poste qui n'en a pas serait punir ceux qui ne sont pas concernés. Vérifié
par mutation : contre une base réellement migrée à la révision précédente, il affiche
l'avertissement et nomme la commande à lancer.

## #040 — Une restauration qui restaure le source mais pas le comportement

**Ce que je croyais.** Qu'après `cp fichier.sauvegarde fichier.py`, le code muté avait
disparu. Le fichier était bien revenu à son contenu d'origine — `grep` le confirmait,
Python relisant le fichier le confirmait aussi.

**Ce qu'il s'est passé.** `make verifier` a rougi sur un test que je venais de voir passer.
Le module importé annonçait `OCCURRENCES_MINIMALES = 2` pendant que le fichier source
disait `3`, et `__file__` pointait bien sur ce fichier-là.

**La cause.** `cp` donne au fichier restauré le mtime de la SAUVEGARDE, antérieur au `.pyc`
compilé pendant la mutation. Python compare ces deux dates pour décider si son cache est à
jour, conclut qu'il l'est, et continue d'exécuter le bytecode muté. Le source et le
comportement divergent alors sans qu'aucune lecture du fichier ne puisse le montrer.

**Pourquoi c'est plus grave qu'un test rouge.** Toute ma méthode de vérification repose sur
la séquence muter → voir rouge → restaurer → voir vert. Si la restauration ne restaure que
le texte, le « voir vert » final ne prouve rien, et surtout : une mutation pouvait rester
active dans le code livré, invisible à la relecture. C'est arrivé ici dans le sens
inoffensif — le test a rougi — mais rien ne garantissait qu'il en soit toujours ainsi.

**Le contrôle en place maintenant.** Restaurer en RÉÉCRIVANT le fichier plutôt qu'en le
copiant : une écriture donne un mtime au présent, postérieur à tout `.pyc`. Le `cp` reste
acceptable s'il est suivi d'un `touch`. Et au moindre doute entre ce que dit le source et
ce que fait le code, purger les `__pycache__` avant de conclure quoi que ce soit — le
désaccord entre les deux est toujours réel, jamais un mirage.

## #041 — Un client qui appelle une route inexistante, et un écran qui appelle ça « Chargement »

**Ce que je croyais.** Que l'écran Foyer était livré. Le client avait sa fonction
`membresDuFoyer`, le serveur sa route `GET /foyer/membres`, les types étaient générés,
`tsc` et `mypy` passaient.

**Ce qu'il s'est passé.** Olivier : « quand elle est vide elle charge en boucle ». La route
est montée sous le routeur `auth`, donc à `/api/auth/foyer/membres` ; le client demandait
`/api/foyer/membres`. Chaque ouverture de l'écran prenait un 404.

**Pourquoi rien ne l'a vu.** Deux défauts qui s'annulent en apparence. Le premier : le
chemin est une CHAÎNE, que `openapi-typescript` ne relie pas à la fonction qui l'utilise —
les types décrivaient parfaitement une route que personne n'appelait. Le second, et le vrai :
l'écran écrivait `membres.length === 0 ? 'Chargement…'`. Une liste vide et une liste pas
encore arrivée y étaient le même état, si bien que **le mode d'échec était rigoureusement
indistinguable du mode normal**. Un `.catch(() => setMembres([]))` complétait le maquillage
en transformant l'erreur en état d'attente.

**Ce que ça dit de plus général.** Un état d'attente affiché par défaut est un état
d'attente qui ment. « Je n'ai rien reçu » et « j'ai reçu qu'il n'y a rien » sont deux
faits différents ; les représenter par la même valeur garantit que la panne ressemblera au
fonctionnement. Le tableau vide comme état initial est le piège, pas le `catch`.

**Le contrôle en place maintenant.** `null` tant que la réponse n'est pas là, un état
d'échec distinct qui propose de réessayer, et `e2e/suppression-foyer.spec.ts` qui exige de
voir un membre — vérifié par mutation en remettant le mauvais chemin : le test rougit.

## #042 — Une protection qui rendait irréversible la seule erreur qu'on fait vraiment

**Ce que je croyais.** Que refuser la suppression d'un compte portant des opérations
protégeait les mois clos. La règle est juste et le test e2e l'affirmait en toutes lettres :
« Le solde d'ouverture EST une opération : le compte n'est donc pas vide. »

**Ce qu'il s'est passé.** Olivier : « je ne peux pas supprimer un espace compte joints même
en étant admin ». Créer un compte en saisissant son solde de départ écrit une opération
d'ouverture. Le compte naissait donc protégé, dès la première seconde, avant d'avoir servi
à quoi que ce soit.

**La cause.** La règle avait été écrite depuis les opérations, pas depuis l'usage. « Ce
compte porte des opérations » et « ce compte a servi » se confondent partout, sauf
exactement dans le cas d'un compte créé par erreur — celui où la suppression compte. Un
amorçage ne clôt aucun mois : il n'y a rien à protéger.

**Ce que ça dit de plus général.** Un test peut verrouiller un bug avec la même force
qu'une fonctionnalité. Celui-ci énonçait la conséquence — l'ouverture bloque — comme si
c'était l'intention, et sa présence rendait le défaut d'autant plus difficile à voir qu'il
avait l'air décidé. Une assertion mérite d'être relue non pas « est-elle vraie ? » mais
« l'a-t-on voulue ? ».

**Le contrôle en place maintenant.** `compte_a_des_operations` ignore `est_ouverture`, et
deux tests d'intégration tiennent les deux bords : un compte qui ne porte que son amorçage
se supprime, un compte qui porte une vraie dépense reste protégé. Vérifiés par deux
mutations opposées — supprimer la protection fait rougir le second, restaurer l'ancien
comportement fait rougir le premier.

## #043 — Un écran qui montre ce qu'il ne peut pas toucher

**Ce que je croyais.** Que #042 avait réglé « impossible de supprimer un compte joint ».
La garde avait été corrigée, deux tests opposés la tenaient, la CI était verte.

**Ce qu'il s'est passé.** Olivier, le lendemain : « j'ai l'espace joint complètement bug et
impossible de le supprimer ». Trois défauts distincts se cachaient derrière la même phrase,
et aucun n'était celui que j'avais corrigé :

1. l'écran de gestion listait les deux périmètres — corrigé exprès pour qu'un compte joint
   soit visible depuis la vue personnelle — mais `PATCH` et `DELETE` continuaient d'exiger
   la vue courante. Le compte s'affichait sous le doigt, le serveur répondait « Compte
   introuvable » ;
2. la liste filtrait `archive = false`. L'écran proposait l'archivage comme l'alternative
   douce à une suppression refusée, et le compte disparaissait de l'écran même qui venait
   de le proposer — ni désarchivable, ni supprimable ;
3. la route des soldes annonçait « archivés compris » dans sa docstring et bouclait sur
   `comptes_visibles`, qui les exclut.

**La cause.** Le correctif précédent avait élargi la LECTURE sans élargir l'ACTION. Une
liste et les opérations unitaires qui la suivent sont un seul geste pour l'utilisateur, et
deux fonctions pour moi : j'ai corrigé celle que le symptôme désignait. La règle des deux
périmètres vivait d'ailleurs dans la route — une boucle `for vue in Vue` posée dans l'API,
loin de `_comptes_autorises` qui en est l'auteur. Une règle recopiée hors de chez elle ne
s'applique qu'aux appelants dont on se souvient.

**Ce que ça dit de plus général.** Afficher un objet est une promesse qu'on peut agir
dessus. Un écran qui liste large et agit étroit ne produit pas un refus, il produit un
mensonge : « introuvable » à propos de quelque chose qui est à l'écran envoie chercher une
panne qui n'existe pas. Et une phrase de docstring — « archivés compris » — a tenu des
semaines parce que rien ne pouvait la contredire : une affirmation sans mesure est une
intention, pas un fait.

**Le contrôle en place maintenant.** `_comptes_administrables` dérive de
`_comptes_autorises` par réunion des deux vues, dans le repository, auteur unique ;
`comptes_a_gerer` et `compte_administrable` s'en servent ; `perimetre_du_compte` calcule
chaque solde dans le monde du compte et non dans la vue courante. Quatre tests
d'intégration, chacun prouvé rouge contre sa faute. Le plus important est celui de la
fuite : remplacer la condition par « tous les comptes du foyer » laisse passer **19 tests
sur 20** — seul `test_le_compte_prive_dun_autre_membre_reste_intouchable` l'attrape. Une
règle de confidentialité élargie n'échoue jamais bruyamment.

## #044 — Un fait de schéma facturé à l'utilisateur

**Ce que je croyais.** Que « supprimer le foyer » était une action claire, et qu'Olivier
l'avait choisie en connaissance de cause : je lui avais posé la question la veille, et il
avait répondu « supprimer le compte pour de bon ». La déconnexion qui suit n'était pas un
bug — c'était la conséquence exacte de ce qui avait été demandé, spécifié et testé.

**Ce qu'il s'est passé.** « Pourquoi quand je supprime un foyer ça me déconnecte, il faut
vraiment dissocier le compte perso / espace perso et l'espace foyer. » Il n'avait pas
changé d'avis sur la suppression définitive : il n'avait jamais voulu qu'arrêter de
partager passe par elle.

**La cause.** En base, `Utilisateur.foyer_id` est non nullable et le foyer porte AUSSI les
comptes personnels : détruire le foyer détruit forcément ses membres. J'ai laissé cette
contrainte de schéma remonter jusqu'à l'écran et devenir une règle d'usage. L'interface
proposait donc l'action que le modèle savait faire, pas celle que l'utilisateur voulait
faire — et ma question de la veille portait sur la première, ce qui la rendait inutile :
en offrant le choix entre deux façons de tout détruire, elle ne pouvait pas révéler qu'il
voulait ne rien détruire du tout.

**Ce que ça dit de plus général.** Une confirmation obtenue ne vaut que pour la question
posée, et une question mal cadrée transforme un accord en preuve trompeuse. Le signe
avant-coureur était là : la vue « comptes joints » est documentée comme un FILTRE sur
`Compte.prive`, pas une entité — donc « supprimer l'espace joint » ne pouvait déjà rien
vouloir dire d'autre que « supprimer ces comptes-là ». J'avais écrit cette phrase moi-même
dans CLAUDE.md sans en tirer la conséquence.

**Le contrôle en place maintenant.** Deux actions, deux écrans, deux jeux d'état :
`DELETE /auth/foyer/partage` supprime les comptes joints sans fermer la session,
`DELETE /auth/moi` efface son compte et confirme par l'ADRESSE — plus par le nom du foyer,
qui désignait la mauvaise chose. Sept tests d'intégration, dont
`test_dissoudre_ne_touche_ni_au_compte_ni_aux_comptes_personnels`, qui mesure les deux
moitiés : ce qui doit disparaître et ce qui doit rester. Un test e2e vérifie que les deux
zones sont sur deux écrans distincts — les réunir ferait revenir le défaut sans qu'aucun
autre test ne le voie.

## #045 — L'écran change de monde avant que les données n'arrivent

**Ce que je croyais.** Que le défaut « Comptes bancaires 2 en vue joints » signalé par Olivier
le 21 août venait uniquement du bundle périmé servi à son téléphone. Le serveur répondait
juste, l'écran affichait faux : le cache expliquait tout.

**Ce qu'il s'est passé.** Un test de bout en bout a échoué sur « element was detached from
the DOM ». En lisant le journal plutôt qu'en durcissant le sélecteur, j'ai vu que le même
état existait dans le code neuf, à l'échelle d'un aller-retour : `basculerVers` posait la
nouvelle vue immédiatement, alors que la liste des comptes appartenait encore à l'ancienne.
Pendant ce court instant, l'écran affichait « Comptes du foyer 2 » — le compteur des
comptes PERSONNELS sous le libellé du foyer.

**La cause.** Deux sources pour un même affichage, mises à jour à des instants différents :
le libellé vient de `vue`, un état local et instantané ; le nombre vient de `comptes`, une
prop rechargée par une requête. Tant qu'elles ne changent pas ensemble, il existe une
fenêtre où l'écran compose une phrase dont chaque moitié est vraie et dont l'ensemble est
faux.

**Ce que ça dit de plus général.** Un chiffre faux ne devient pas acceptable parce qu'il ne
dure pas — il est simplement plus difficile à attraper, et c'est pire : on le voit sans
pouvoir le reproduire, donc on doute de soi plutôt que du programme. Et ce défaut ne se
serait jamais montré sans un test qui a échoué pour une autre raison : le durcir sans lire
son journal l'aurait enterré. Un test qui échoue est d'abord un témoin, pas un obstacle.

**Le contrôle en place maintenant.** `basculerVers` est asynchrone : l'en-tête de vue part
d'abord — c'est lui qui décide du périmètre servi — puis on ATTEND le rechargement avant de
poser `vue`. L'écran montre l'ancien monde, entièrement cohérent, jusqu'à ce que le nouveau
soit là.

## #046 — Un fait de schéma raconté comme un fait social

**Ce que je croyais.** Que l'écran « Foyer » décrivait un groupe : des membres, un partage,
une invitation. Il affichait « Membres » et la liste de ceux qui en font partie.

**Ce qu'il s'est passé.** Olivier, seul dans son foyer : « pourquoi il me dit membre d'un
foyer alors que non, et pourquoi je peux pas le quitter non plus ? » L'écran lui annonçait
qu'il était membre d'un groupe d'une personne — lui — sans porte de sortie. Sur la même
capture, la zone « Dissoudre le partage » était dépliée sur son propre refus : « il n'y a
aucun compte joint à dissoudre ». Un bouton qui ne pouvait qu'échouer.

**La cause.** `Utilisateur.foyer_id` est non nullable : tout compte reçoit un foyer d'office,
créé par `creer_premier_compte`. C'est un conteneur technique — le point d'accroche des
comptes, catégories et enveloppes — et je l'ai exposé sous son nom de modèle, avec son
vocabulaire de modèle. « Membre » est vrai dans la base et faux dans la vie : on n'est pas
membre d'un groupe qu'on n'a jamais rejoint et dont on est seul.

**Ce que ça dit de plus général.** Deux occurrences en deux jours pour la même cause : #044
faisait payer à l'utilisateur la contrainte « le foyer contient tout » ; celle-ci lui fait
lire le mot « foyer » à la place de « votre espace ». Un modèle de données a le droit
d'avoir ses noms ; l'écran n'a pas le droit de les emprunter sans se demander ce qu'ils
affirment. Et une action ne se propose pas quand son échec est certain : l'écran savait
qu'il n'y avait aucun compte joint, il le savait avant de proposer.

**Le contrôle en place maintenant.** Le titre devient « Partage » et la liste cède la place
à « Vous n'avez encore partagé avec personne » tant qu'on est seul ; « Dissoudre le
partage » n'apparaît que s'il existe un compte joint. Deux tests e2e, dont un qui mesure la
règle dans les DEUX sens en lisant l'état réel du foyer — une assertion qui ne vaudrait que
dans un cas passerait aussi pour un code qui affiche la zone toujours, ou jamais.

**Ce qui reste faux et n'est pas corrigé.** On ne peut toujours pas QUITTER un foyer quand
on y a été invité : il faudrait un foyer d'accueil, le déplacement des comptes personnels
et la duplication des catégories utilisées, puisqu'elles appartiennent au foyer. Seul
« supprimer mon compte » existe. La limite est connue et écrite, elle n'est pas résolue.
