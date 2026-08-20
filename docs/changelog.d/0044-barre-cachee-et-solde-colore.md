# Barres de défilement masquées, solde coloré par son signe

- **Aucune barre de défilement visible.** Le défilement reste entier : seule sa barre
  disparaît. Ce que ce choix coûte est réel — sur grand écran, la barre est le seul indice
  qu'il reste du contenu plus bas. L'application vise d'abord le téléphone, où c'est une
  incrustation qui s'efface au repos. Le témoin mesure DEUX choses qui ne bougent pas
  ensemble : épaisseur nulle **et** page toujours défilable — vérifier seulement la
  première ne distinguerait pas une barre masquée d'une page bloquée en `overflow: hidden`.

- **Le solde de l'accueil prend la couleur de son signe**, rouge ou vert, avec une lueur
  assortie derrière lui.

## Pourquoi le dégradé est derrière et non sur le chiffre

Un dégradé posé sur du texte passe par `background-clip: text`, ce qui rend la couleur du
texte **transparente**. La sonde de contraste lit `color` : elle mesurerait alors 1:1 et ne
pourrait plus rien garantir sur le chiffre le plus important de l'écran.

La couleur du solde est donc **pleine**, et le dégradé vit dans la lueur posée derrière —
un halo qui ne porte aucun texte. Les six combinaisons thème × transparence restent vertes.
