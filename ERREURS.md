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
