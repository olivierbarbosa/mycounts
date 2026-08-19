# Authentification, foyer et invitations (lot 1, backend)

**Lot** : 1 | **Date** : 2026-08-19

## Ajouté

- Tables `foyer`, `utilisateur`, `invitation`, `session_web` + migration Alembic.
  `foyer_id` est présent dès maintenant bien que l'interface n'expose aucun partage :
  l'ajouter après coup obligerait à toucher chaque requête de lecture du projet.
- `domain/securite.py` — Argon2id (64 Mio, 3 passes), jetons de 256 bits, expirations.
- `repository/auth.py` — seul endroit du projet qui construit une requête.
- Routes `/auth/connexion`, `/deconnexion`, `/moi`, `/invitations`, `/rejoindre`.
- `scripts/creer_premier_compte.py` — aucune inscription publique n'existe.

## Choix de sécurité, et pourquoi

- **Cookie `httponly` + `samesite=lax`**, `secure` hors développement. Un jeton en
  `localStorage` serait lisible par le premier XSS venu.
- **Empreinte-leurre Argon2** quand l'adresse est inconnue. Sans elle, une adresse sans
  compte répond en ~1 ms et une adresse connue en ~60 ms : mesuré à **12,5×** d'écart,
  directement observable de l'extérieur. Avec le leurre, le rapport retombe sous 1,3×.
- **Codes d'invitation stockés hachés**, usage unique, 7 jours. Une fuite de la base ne
  permet pas de rejoindre un foyer.
- **Sessions expirées filtrées en SQL**, jamais en Python : une session périmée ne remonte
  pas jusqu'à un appelant qui pourrait oublier de la vérifier.
- **Mot de passe : 12 caractères minimum, sans règle de composition.** Les règles de
  composition produisent des mots de passe plus courts et plus prévisibles.

## Vérifié

32 tests d'intégration contre PostgreSQL et l'application réelle. Trois témoins ont été
exécutés contre leur implémentation fautive :

- sans l'empreinte-leurre, le test de temps de réponse échoue (rapport 12,5×) ;
- avec une route ajoutée sans authentification, le test d'isolation échoue ;
- la migration descend jusqu'à `base` et remonte sans écart.

Voir ERREURS.md #005 : la première version du test d'isolation itérait sur une liste vide.
