# Direction artistique néon et Liquid Glass

**Lot** : 1 (révision) | **Date** : 2026-08-19

Révise la DA à la demande : fond en dégradé violet profond au lieu d'un aplat quasi noir,
surfaces en verre laiteux étendues aux cartes de contenu, accents électriques, lueurs
néon, champs et boutons en pilule.

## La règle qui change, et sa contrepartie

Le lot 1 posait « aucun montant n'est jamais sur du verre ». Cette règle est **remplacée**,
pas abandonnée : tout texte visible doit atteindre un contraste AA de 4,5:1, vérifié
automatiquement dans les **deux thèmes** et les **trois positions** du réglage de
transparence — six combinaisons, sur les couleurs réellement rendues et non sur les
valeurs annoncées par la palette.

Conséquence directe : deux teintes ont dû changer, non par goût mais par mesure.
`texteFaible` passe de 45 % à 62 % d'opacité (3,49:1 → au-dessus du seuil), et l'accent de
`#8B5CF6` à `#7C3AED` (4,23:1 avec du blanc → 5,7:1). Le néon reste présent par les
lueurs et les liserés, qui ne portent jamais de texte.

## Vérifié

19 tests de bout en bout, dont 6 de contraste. Playwright crée désormais lui-même le
compte de démonstration (`globalSetup`) : les tests d'intégration vidaient les tables et
faisaient échouer la suite e2e lancée seule.

Voir ERREURS.md #011 : la première version de la sonde de contraste mesurait faux — elle
lisait `color(srgb …)` comme du 0–255 — et allait me faire éclaircir des couleurs qui
n'avaient aucun problème.
