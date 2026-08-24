# Le socle de la V1 devient publiable

Trois documents fixent désormais le produit, son architecture et son ordre d'exécution :
`V1-PRODUIT.md`, `V1-ARCHITECTURE.md` et `V1-ROADMAP.md`. Ils actent notamment l'identité
séparée des espaces financiers, l'onboarding MFA, les imports CSV/PDF à validation humaine,
les cycles de paie persistés, les enveloppes couvertes par l'épargne réelle, le coach IA
consenti et la trajectoire PWA puis Capacitor.

Le premier lot corrige aussi quatre défauts du socle existant :

- un `PATCH` peut réellement retirer une catégorie ou une date avec `null`, sans confondre
  ce choix avec un champ omis ;
- `/health` mesure un aller-retour PostgreSQL et rend 503 si la base est indisponible ;
- un code TOTP accepté est consommé atomiquement et ne peut plus être rejoué ;
- les échecs de mot de passe et de MFA sont limités par couple identifiant/origine et par
  origine dans une fenêtre PostgreSQL, avec seulement des pseudonymes HMAC en base ;
- les pseudonymes expirés sont purgés par la sonde interne, et Uvicorn n'accepte les
  en-têtes d'origine que du conteneur Traefik explicitement résolu ;
- la déconnexion révoque enfin le jeton côté serveur au lieu de seulement effacer le
  cookie du navigateur.

La clé HMAC devient obligatoire hors développement. La CI exécute désormais le vrai lint
frontend et le build Vite de production, en plus du typage, des tests et des parcours
navigateur.

La connexion n'est plus une carte web posée au centre : elle devient l'écran d'entrée
plein format de l'application, avec les identifiants en un geste puis une étape MFA dédiée
uniquement lorsque le compte la demande. Les codes TOTP et de secours sont enfin pris en
charge par le frontend.
