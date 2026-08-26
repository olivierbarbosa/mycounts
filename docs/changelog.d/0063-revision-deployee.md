# Le déploiement automatique regarde ce qui tourne

- L'image de l'API porte la révision déployée en étiquette OCI, renseignée par
  `deployer.sh` au moment de la construction.
- `deployer-auto.sh` compare cette étiquette à `origin/<branche>`, et non plus le `HEAD`
  de son arbre de travail : un arbre avancé à la main sans déploiement ne rend plus le
  retard invisible.
- Une image d'avant ce lot ne porte pas d'étiquette et vaut « aucune », donc redéploie :
  un doute se résout en reconstruisant, jamais en supposant à jour.
