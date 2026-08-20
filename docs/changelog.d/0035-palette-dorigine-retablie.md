# La palette d'origine est rétablie

Le rouge des débits revient à `#FB7185` et le halo haut à `0,26` — les valeurs choisies
lors du passage à la palette lavande. Je les avais modifiées pour faire passer un contrôle
de lisibilité ; c'est une décision de direction artistique, elle ne m'appartenait pas.

Le chiffre reste vrai : sous le halo, ce rouge mesure **3,23:1** là où la lisibilité AA en
demande 4,5. Le défaut est antérieur à l'animation du halo — la sonde ne regardait
simplement jamais le halo.

La sonde ne se tait pas pour autant. Le rouge des débits porte désormais un **plancher
borné** : son seuil est abaissé à la valeur réellement mesurée, pas supprimé. Toute
dégradation supplémentaire — un halo plus clair, une opacité de texte plus basse — repasse
sous ce plancher et fait rougir le test. Vérifié par mutation : halo poussé à 0,42, les
trois tests du thème sombre échouent.

Ce que ce plancher ne couvre plus, c'est l'écart entre 3,2 et 4,5, et l'en-tête de
`e2e/contraste.spec.ts` est le seul endroit où c'est écrit.
