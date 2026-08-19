# Les halos traversent la page, et la sonde de contraste les voit enfin

Les deux halos radiaux quittent le `background-image` de `body` pour un pseudo-élément
animé par `transform` : ils parcourent **100 % de la largeur de l'écran et 90 % de sa
hauteur** en 78 s, à 61 images/s sur un écran de 390 px.

`transform` est le seul canal animé, et pas pour des raisons de fluidité : translater,
tourner et agrandir déplacent le halo sans créer une seule couleur nouvelle. L'ensemble
des teintes qu'il peut poser sous un texte reste ses arrêts de dégradé, donc la mesure de
contraste garde un sens.

## Un défaut de lisibilité antérieur, révélé au passage

La sonde n'inspectait les dégradés que sur l'élément de texte lui-même et ne remontait les
ancêtres qu'en lisant `backgroundColor`. **Les halos lui échappaient entièrement** : elle
mesurait le fond nu et se déclarait verte pendant que le halo éclaircissait réellement le
fond sous les montants.

Une fois rendue capable de les voir, elle a trouvé 32 textes sous le seuil : le rouge des
débits tombait à **3,23:1** contre 4,5 exigés. Corrigé en éclaircissant `debit`
(`#FB7185` → `#FC9DAB`) et en ramenant `haloHaut` de 0,26 à 0,20 — au-delà, le vert des
crédits restait collé à 4,52:1, sans marge pour la moindre retouche future.

Le halo s'immobilise sous `prefers-reduced-motion`.
