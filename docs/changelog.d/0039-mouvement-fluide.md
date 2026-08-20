# Le mouvement des écrans devient fluide, et les sous-menus en ont un

Deux défauts, tous deux invisibles aux tests d'alors.

**Les sous-menus n'étaient pas animés du tout.** Un module CSS renomme les `animation-name`
qu'il rencontre : en déplaçant les images clés dans `global.css`, les modules pointaient
vers un nom inexistant, et le navigateur ignorait la déclaration sans rien dire. Le
mouvement est désormais exposé en **classes globales**, qui ne sont pas renommées.

**Le panneau animait `clip-path`**, que le compositeur ne sait pas jouer : une repeinte
plein écran par image, sous un verre qui refait son flou. Mesuré à **33,3 ms par image —
trente par seconde**. Remplacé par `scale` et `opacity` depuis l'origine de la bulle, et
le verre est suspendu le temps de chaque mouvement : **16,7 ms, soit soixante**.

Revenir d'un sous-menu le fait maintenant **repartir vers la droite**, d'où il venait. Son
démontage est piloté par la fin de l'animation et non par un délai recopié : deux durées à
tenir d'accord finissent toujours par diverger.

Garde-fou `e2e/mouvement.spec.ts` : chaque écran doit animer quelque chose, et seulement
des propriétés compositables. Il ne chronomètre rien — une mesure de temps serait instable
en intégration continue — il vérifie les deux causes, qui sont déterministes.
