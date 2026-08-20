# Le thème se choisit, au lieu de subir celui du téléphone

`tokens.ts` savait lire `data-theme` depuis le premier jour, mais **rien ne l'écrivait** :
l'application suivait `prefers-color-scheme` sans recours. Un iPhone réglé sur
« automatique » la faisait donc basculer en clair au lever du jour, sans qu'aucun écran ne
permette de s'y opposer.

Paramètres → Apparence propose désormais Système, Sombre ou Clair. « Système » reste le
défaut, et retire l'attribut plutôt que d'en écrire un troisième : c'est son ABSENCE que
la feuille de tokens interprète comme « suis le téléphone ».

Le choix est appliqué **avant le premier rendu**, sinon l'écran s'affiche une fraction de
seconde dans le thème du système avant de basculer — un clignotement d'autant plus visible
que les deux thèmes s'opposent.

Le témoin mesure les **deux sens** : téléphone en clair avec choix sombre, puis téléphone
en sombre avec choix clair. Ne vérifier qu'un sens ne distinguerait pas un réglage qui
fonctionne d'un réglage bloqué sur une seule valeur. Et il vérifie que le choix survit au
rechargement : un réglage qui se perd est pire que pas de réglage, il donne l'impression
d'avoir été ignoré.
