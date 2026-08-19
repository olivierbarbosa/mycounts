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
