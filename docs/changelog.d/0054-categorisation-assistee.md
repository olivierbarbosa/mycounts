# Catégorisation assistée à l'import

Demandée par Olivier le 20 août 2026, qui a fourni sa clé OpenRouter et accepté, après
qu'on lui a montré ce que contiendraient les libellés — y compris ceux qui trahissent un
rendez-vous médical — que ceux-ci sortent du foyer.

## Quatre niveaux, du moins coûteux au plus coûteux

Chaque niveau ne voit que ce que le précédent n'a pas su ranger. **L'ordre n'est pas une
optimisation : chaque niveau franchi est un libellé de moins qui sort du foyer.**

1. **Ce que le foyer a explicitement rangé ainsi** — appris aux imports précédents ;
2. **le tableau par défaut** des catégories bancaires. Mesuré sur l'export réel d'Olivier :
   **99 lignes sur 198**, dont 90 des 135 dépenses, sans qu'aucun libellé ne sorte ;
3. **l'assistance externe**, pour le reste seulement ;
4. rien — et c'est une réponse. Ranger de travers est pire que ne pas ranger : une
   opération sans catégorie se VOIT dans les statistiques, une opération mal rangée
   disparaît dans un total juste en apparence.

## Une seule porte de sortie, et le garde-fou qui le vérifie

`services/categorisation_ia.py` est le **seul fichier du projet autorisé à parler à un
tiers**. Le garde-fou nº 3 a changé de nature pour le vérifier — sa propre docstring
l'annonçait depuis le début :

> « Le jour où une catégorisation assistée arrive, elle apporte dans LE MÊME COMMIT
>   l'analyse statique des sources vérifiant que les libellés sont anonymisés. »

Il contrôle désormais trois choses : qu'un seul fichier mentionne un hôte externe, que ce
fichier ne nomme aucun champ bancaire dans son CODE — par l'arbre syntaxique, pas par une
expression régulière, sa docstring citant précisément ces champs pour dire qu'ils ne
sortent pas — et qu'aucun SDK LLM n'entre dans les dépendances. L'appel se fait en HTTP
simple : un SDK ouvrirait des chemins d'envoi que ce contrôle ne saurait pas lire.

Vérifié par trois mutations : un montant introduit dans la porte de sortie, un second
fichier appelant OpenRouter, un SDK ajouté au `pyproject.toml`. Les trois sont détectés.

## Ce qui sort, et ce qui ne sort pas

Sortent : des **libellés de commerçants**. Ne sortent jamais : montants, dates, soldes,
numéros de compte, identifiants de foyer, références bancaires. La fonction prend une liste
de `str` — ce n'est pas une politesse d'écriture, c'est ce qui rend la promesse vérifiable
par lecture du seul prototype.

## Le filtrage par nature, appris d'une mesure ratée

Une première version envoyait tous les libellés ensemble avec toutes les catégories. Elle
rendait « Revolut → Autres revenus », « BPCE Vie → Autres revenus », « Caisse d'Épargne →
Autres revenus » : privé du signe, le modèle rangeait des DÉPENSES en recettes.

Le corriger n'a pas demandé d'envoyer davantage. Les dépenses et les revenus sont demandés
séparément, chacun avec les seules catégories de sa nature — il suffisait de ne pas
proposer une catégorie que la nature interdit. Les suggestions sont devenues justes, et le
modèle nettement plus prudent : dix propositions au lieu de vingt-cinq, mais utilisables.

## Jamais bloquant

Clé absente, service en panne, réponse illisible : la fonction rend un dictionnaire vide et
l'import continue exactement comme avant. Une catégorisation est un confort ; en faire une
dépendance rendrait l'import tributaire d'un tiers pour une tâche qu'il sait faire sans lui.

Sans clé, les deux premiers niveaux rangent déjà les deux tiers d'un relevé.

## Deux garde-fous corrigés en chemin

**Le n°2 rougissait sur `.env`** — un fichier gitignoré, fait précisément pour contenir des
secrets. Il parcourait le disque alors que sa docstring promettait « les fichiers
versionnables ». Il demande maintenant à git la liste de ce qui peut partir dans un commit.
Un contrôle qui rougit devant une situation correcte finit par être désactivé, et c'est
alors le vrai cas qui passe.

**Les dates des tests basculaient en UTC.** `new Date().toISOString().slice(0, 10)` est
l'équivalent JavaScript du `::date` nu que ce dépôt proscrit en SQL. Le défaut ne se voyait
qu'entre minuit et deux heures du matin — constaté le 21 août à 00h21 : « demain » rendait
le 21, c'est-à-dire aujourd'hui à Paris, et l'échéance se trouvait matérialisée. Douze
occurrences corrigées, un helper `dates.ts` les remplace.

Et une régression que j'ai introduite en corrigeant le premier : la paie du jour que
j'avais ajoutée pour stabiliser un test ouvrait une NOUVELLE période, faisant sortir de
l'accueil les opérations datées d'hier de tous les tests suivants. Un test qui déplace la
période d'un foyer partagé déplace le sol sous les autres.

## Proposer une catégorie qui manque

Demandé par Olivier après avoir vu « RADIO VETERINAIRE » n'aller nulle part : ce n'est pas
de la santé, ce n'est pas des courses, il manque « Animaux ».

L'écran propose désormais les catégories que le relevé appellerait et que le foyer n'a pas
— avec un bouton pour les créer, jamais de création d'office.

**Jamais pour un seul libellé.** C'est la règle qui empêche cette fonctionnalité de devenir
insupportable : sans elle, chaque commerçant inconnu produirait sa propre catégorie et
l'écran offrirait d'en créer trente. Une catégorie qui ne servirait qu'une fois n'est pas
une catégorie, c'est un libellé.

Sont écartés aussi : les noms qui existent déjà, quelle qu'en soit la casse — le modèle en
propose volontiers un déjà présent, et l'écran offrirait alors de créer un doublon — et
ceux trop longs pour tenir dans une pastille.

Éprouvé sur les orphelins réels du relevé d'Olivier : « Soins Animaux » couvrant ses trois
lignes vétérinaires, « Meubles » couvrant deux achats de mobilier, et rien pour le libellé
isolé.

## L'écran d'import, refait

Olivier l'a essayé sur son téléphone : « c'est tellement compliqué à lire ». Il avait
raison. La version précédente affichait les deux cents lignes à l'identique, chacune avec
une case à cocher, un libellé, une date, une catégorie bancaire, **deux menus déroulants**
et un montant. Sur 390 px, c'est illisible.

Le principe de la refonte : **sur un relevé, la plupart des lignes ne demandent aucune
décision**, et faire payer à toutes le coût des quelques-unes qui en demandent une est
exactement ce qui rend un écran impraticable.

Ne sont donc dépliées que les lignes qui CHANGENT LE RÉSULTAT :

- un doublon probable, qui compterait une dépense deux fois ;
- un virement sans compte de contrepartie, qui serait écrit comme un revenu.

Une ligne simplement dépourvue de catégorie n'y figure pas : elle s'importe très bien sans,
et il y en a quarante. Le compteur du repli l'indique — « 42 prêtes, dont 12 sans
catégorie » — pour que le repli ne cache pas une information dont on pourrait vouloir
s'occuper.

Les menus déroulants ont disparu des lignes. Une ligne MONTRE ce qu'elle est ; qui veut la
corriger la touche, et une feuille s'ouvre. Toute la ligne est une cible tactile : viser un
petit contrôle au sein d'une ligne est le meilleur moyen de rater son geste sur téléphone.

Deux défauts trouvés en refaisant les tests : le dépôt d'un fichier ne réinitialisait pas
l'état de dépliage, si bien qu'un second dépôt s'ouvrait déjà déplié — le même geste
donnant deux résultats ; et le helper de test cliquait sans regarder `aria-expanded`, donc
repliait ce qu'il devait déplier.
