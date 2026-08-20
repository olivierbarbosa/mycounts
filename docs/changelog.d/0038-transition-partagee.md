# La bulle d'avatar se déploie en panneau

Ouvrir les paramètres n'est plus une glissade : le panneau **éclôt du disque de la bulle**
(`clip-path` circulaire) pendant que l'avatar y **migre** — transition d'élément partagé,
en FLIP : on mesure l'arrivée, on calcule le transform qui ramènerait l'avatar sur la
bulle, on joue l'inverse. Mesurer plutôt que deviner le trajet est ce qui rend l'effet
juste sur tous les écrans ; une trajectoire écrite à la main serait fausse partout sauf
sur l'appareil qui a servi à l'écrire.

Le panneau est en **verre dépoli** : l'application reste devinée derrière, ce qui dit
qu'elle est recouverte et non remplacée. 94 % d'opacité et non 70 — le texte doit garder
le contraste d'un fond connu, or ce qui passe derrière est l'écran de l'utilisateur.

## Deux mesures qui ont changé le résultat

- L'avatar partait de sa position d'ARRIVÉE, à 198 px de la bulle : deux animations se
  superposaient, la seconde mesurant une position déjà déplacée par la première. L'effet
  existait dans le code et nulle part à l'écran.
- Le débit tombait de 61 à **36 images par seconde**. Un `backdrop-filter` plein écran
  refait son flou à chaque image tant que ce qu'il recouvre bouge — et les halos voyagent.
  Ils se figent désormais tant qu'un écran les recouvre : **55 images par seconde**, et
  rien de visible n'est perdu puisqu'ils sont cachés.

Le témoin d'épargne cesse au passage de comparer des chaînes d'en-tête : il mesure les
grandeurs exactes. Comparer du texte entier le faisait échouer dès qu'une échéance sans
rapport se matérialisait.
