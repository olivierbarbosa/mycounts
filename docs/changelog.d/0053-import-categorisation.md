# Lot F (suite) — rendre l'import réellement utilisable

Le lot F savait lire un relevé. Il en tirait 198 lignes **sans aucune catégorie**, ce qui
rendait muets les statistiques et les budgets, et rien n'empêchait un abonnement d'être
compté deux fois. Cette suite règle les trois points.

## Le rangement s'apprend

Une correspondance retenue à chaque validation, sur deux niveaux :

- le **commerçant** normalisé — « intermarche → Courses » ;
- la **catégorie de la banque** — « Alimentation → Courses », qui couvre d'un coup tous
  les commerçants de cette catégorie, y compris ceux qu'on n'a jamais vus.

Le particulier l'emporte sur le général, comme pour le budget mensuel d'une enveloppe : une
règle écrite pour un commerçant précis passe avant une règle large.

Rien n'est proposé quand rien n'a été appris. Ranger de travers est pire que ne pas ranger
— une opération sans catégorie se VOIT dans les statistiques, c'est même la ligne la plus
visible, alors qu'une opération mal rangée disparaît dans un total juste en apparence.

## Les doublons avec les récurrences sont signalés

Un abonnement saisi comme récurrence a déjà produit son opération ; le relevé la contient
aussi. Sans rapprochement, il compte deux fois — dans le solde, les budgets et les
statistiques.

Le critère est le **montant exact et une date proche**, jamais le libellé : une récurrence
s'appelle « Netflix » chez son propriétaire et « PRLV NETFLIX INTERNATIONAL BV » sur le
relevé, et exiger la ressemblance ferait rater précisément les cas visés.

La ligne est **décochée et dit pourquoi**. Décochée parce qu'une opération en double fausse
trois chiffres d'un coup, alors qu'une ligne oubliée se rattrape en la recochant. Elle
n'est jamais supprimée : deux dépenses du même montant à trois jours d'intervalle existent,
et seule la personne qui les a faites peut trancher.

## Les prélèvements réguliers sont repérés

Demandé par Olivier, avec une exigence explicite : *pas de bruit inutile ou non traitable*.
Le seuil a donc été **calibré sur ses vrais relevés**, et corrigé par ce calibrage.

La première version exigeait trois occurrences et n'en proposait **aucune** sur un export
de 198 opérations. La raison tient en une ligne : l'export couvrait 55 jours, où un
prélèvement mensuel ne peut apparaître que deux fois. Un seuil fixe demandait l'impossible,
et se serait tu pour toujours sans jamais signaler qu'il ne cherchait pas.

Le seuil est désormais **relatif à ce que la fenêtre permet d'observer** : trois occurrences
quand le relevé est assez long pour en contenir trois, deux quand il ne peut pas. Mesuré :

| Règle | Propositions sur 198 opérations, 55 jours |
|---|---|
| Seuil fixe à 3 | **0** — inutilisable |
| Seuil fixe à 2 | 12, dont deux « hebdomadaires » douteux |
| **Seuil relatif** | **10**, toutes de vrais abonnements |

Les deux écartées par le seuil relatif sont précisément les fausses : sur 55 jours une
cadence hebdomadaire permet huit occurrences, le seuil y monte donc à trois.

Ce que la détection ne trouve PAS, et il vaut mieux le savoir : un prélèvement dont le
montant varie — l'électricité, l'eau. Les repérer demanderait une tolérance sur le montant,
qui rapprocherait aussi des dépenses sans aucun rapport, et le prix serait payé en
suggestions fausses.

Rien n'est créé. Un écran qui ajouterait des récurrences tout seul remplirait le calendrier
de prélèvements que personne n'a validés, et il faudrait ensuite les défaire un par un.

## Un défaut silencieux trouvé en chemin

`categorie_proposee` compare ses genres avec `is`, qui est le bon opérateur pour une
énumération. Mais la colonne est un `String`, et SQLAlchemy en rend une chaîne brute :
`'libelle' is GenreCorrespondance.LIBELLE` vaut `False` là où `==` vaudrait `True`. La
correspondance n'était jamais retrouvée, **sans qu'aucune erreur ne se produise nulle
part**. Le repository convertit désormais explicitement.

## Vérifié

39 tests unitaires, dont une mutation sur le seuil relatif — le remplacer par une constante
basse fait rougir le témoin de la longue fenêtre. 180 d'intégration, 113 de bout en bout.
