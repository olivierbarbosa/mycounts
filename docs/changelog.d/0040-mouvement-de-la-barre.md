# La barre d'onglets bouge, et les pages entrent du bon côté

- **Pastille glissante** : un seul élément qui se déplace d'un onglet à l'autre, au lieu
  d'un fond qui s'allume sur l'arrivée. Le déplacement dit d'où l'on vient. Les onglets
  étant à largeur égale, sa position se calcule d'un index — rien à mesurer.
- **Rebond de l'icône** choisie, court et sans mollesse : un changement d'onglet est
  fréquent, et une animation qu'on subit dix fois par jour doit se remarquer sans se faire
  attendre. Plus un enfoncement au toucher, pour qu'un appui sur l'onglet déjà actif
  produise quand même un signe.
- **Sens d'entrée des pages** : aller vers la droite dans la barre fait arriver la page par
  la droite, revenir vers la gauche la fait arriver par la gauche. Sans mémoire du
  déplacement, toutes entreraient du même côté et le mouvement ne dirait plus rien du
  parcours — il ne serait que du bruit.

Tout est joué par `transform` et `scale`, que le compositeur exécute sans repeindre : le
changement d'onglet mesure **16,7 ms par image**, soit soixante par seconde, au-dessus du
verre de la barre.

Au format bureau la pastille disparaît : le rail empile ses onglets sous une marque, et
entretenir une seconde géométrie pour un glissement vertical coûterait plus qu'il
n'apporte. Ce que ce choix coûte est écrit dans la feuille de style.

## Une complexité retirée par la mesure

L'icône était remontée à chaque changement, via une clé React, pour forcer le rejeu de son
animation. Le témoin est resté **vert sans cette clé** : une animation CSS démarre dès que
son `animation-name` s'applique, et la classe change déjà d'un onglet à l'autre. La clé ne
servait à rien ; elle est partie.
