# mycounts

Application de gestion de budget de foyer : saisie des dépenses et des revenus, agenda
des prélèvements, plafonds par catégorie.

**Ce fichier décrit l'état RÉEL du projet.** S'il diverge du code, le code a raison et ce
fichier se corrige dans le même commit. Toute ligne ici doit pointer vers un fichier
existant : une ligne sans fichier est une intention, sa place est dans le plan ou dans
`BOUCLE.md`.

## État : lot 2 terminé

Existe : authentification et foyer, comptes privés, catégories (créer / renommer /
retinter / archiver / supprimer), opérations, période budgétaire de paie à paie, soldes
et liste, amorçage avec solde d'ouverture. Interface néon + Liquid Glass, mobile-first
avec rail latéral au-delà de 1024 px.

**N'existe pas encore** : récurrences et agenda (lot 3), plafonds (lot 4), comptes joints
et partage (lot 5), déploiement VPS (lot 6).

## Stack

Python 3.12 · FastAPI · PostgreSQL 16 · SQLAlchemy 2 · Alembic · React + Vite +
TypeScript · CSS Modules · Playwright. Tout est en français : noms de fonctions, de
variables, de composants et de tests.

## Commandes

```bash
make installer          # venv + dépendances
make db-haut            # PostgreSQL sur le port 5434 + migrations (5433 est pris ailleurs)
make verifier           # lint + types + garde-fous + tests unitaires
make tests-integration  # tests contre le vrai PostgreSQL
make tests-e2e          # mise en page sur 390/820/1280 px dans un vrai navigateur
```

La liste des contrôles vit dans le `Makefile` et nulle part ailleurs ; la CI l'appelle.

## Règles en vigueur

- **Un montant est un entier de centimes** — `Cents` dans `backend/mycounts/domain/montants.py`.
  Aucun flottant dans `domain/`, vérifié par `scripts/verifier_pas_de_float.py`.
- **Les dates civiles sont en Europe/Paris** — `backend/mycounts/domain/calendrier.py`.
  En SQL, toujours `AT TIME ZONE 'Europe/Paris'`, jamais `::date` nu : le cast nu dépend
  du fuseau de session du serveur (mesuré, voir `tests/integration/test_socle_base.py`).
- **`bornes_du_mois()` est le mois CIVIL**, pas la période budgétaire — celle-ci vit dans
  `domain/periode.py` et va de paie à paie. Ne jamais utiliser l'un pour l'autre.
- **Un solde d'ouverture est une opération** (`est_ouverture`), pas une colonne. Il compte
  dans les soldes, jamais dans les dépenses.
- **La nature d'une catégorie (dépense / revenu) n'est pas modifiable** : la changer
  inverserait le signe attendu des opérations déjà classées, et donc des mois clos.
- **Toute l'API vit sous `/api`** — un seul préfixe, aucune liste de chemins à
  synchroniser avec le proxy de développement.
- **Toute requête passe par `backend/mycounts/repository/`** — `scripts/verifier_scope_repository.py`
  refuse tout `select`/`execute` écrit ailleurs dans `backend/mycounts/`. Chaque lecture
  de données de foyer prend un `Principal` : le périmètre n'est jamais implicite.
- **Aucune inscription publique.** Premier compte par `scripts/creer_premier_compte.py`,
  les autres par code d'invitation (haché, usage unique, 7 jours).
- **Une adresse électronique est validée par `normaliser_courriel()`**, dans le domaine.
  Le schéma d'API l'appelle via `AfterValidator` — pas d'`EmailStr`, qui ferait un second
  auteur de la règle.
- **Frontend : `design/tokens.ts` est l'auteur unique de la palette.** Les composants
  n'écrivent que `var(--…)`. DA néon + Liquid Glass : dégradé violet, surfaces en verre.
  Un texte PEUT être posé sur du verre, à une condition mesurée — contraste AA de 4,5:1
  vérifié dans les deux thèmes et les trois positions de transparence
  (`frontend/e2e/contraste.spec.ts`). Les opacités de texte et la teinte de l'accent sont
  donc contraintes par la mesure, pas choisies à l'œil.
- **Mobile d'abord, bureau à part entière.** Media queries `min-width` uniquement. À
  partir de 1024 px la navigation devient un rail latéral — pas une tab bar centrée dans
  le vide.
- **Session en cookie `httponly` + `samesite=lax`**, jamais en `localStorage`. Une adresse
  inconnue et un mot de passe faux produisent la même réponse ET le même temps de réponse
  (empreinte-leurre Argon2 — sans elle, l'écart mesuré est de 12,5×).

## Garde-fous actifs

Dix, tous bloquants, tous prouvés en les faisant échouer devant la faute qu'ils
prétendent détecter : données bancaires (IBAN mod-97, PAN Luhn), secrets, dépendances LLM,
tête Alembic unique, flottants dans le domaine, requêtes hors repository, couleurs en dur
hors `tokens.ts`, et mise en page sur trois tailles d'écran. Chaque script documente en
tête **ce qu'il ne détecte pas** — lire cette section avant de lui faire confiance.

## Habitudes

- Une mesure qui ne peut pas rendre la réponse inverse ne prouve rien. Avant d'accepter un
  test ou un chiffre : *dans quel cas aurait-il donné l'autre résultat ?* Si la réponse est
  « aucun », l'exécuter contre l'implémentation fautive.
- Valider par le chemin de production : PostgreSQL réel, pas SQLite ; l'écran, pas `curl`.
- **Vérification verte AVANT d'ouvrir le lot suivant**, toujours : `make verifier`,
  `make tests-integration`, `make tests-e2e`, puis la CI réellement passée. Deux pièges,
  tous deux rencontrés : un job vert dont les tests ont été *skippés* ne prouve rien
  (lire les compteurs), et `gh run list --limit 1` renvoie souvent l'exécution du commit
  PRÉCÉDENT — sélectionner par `headSha == git rev-parse HEAD`.
- `ERREURS.md` se relit avant de toucher une zone où je me suis déjà trompé. La forme la
  plus fréquente, cinq entrées sur dix-sept : *la mesure porte sur le mauvais sujet* —
  mauvaise machine, mauvais port, mauvais commit, mauvais état du serveur.
- **Un témoin qui modifie du code serveur exige un redémarrage d'uvicorn** avant d'être
  cru, et une vérification que le fichier est bien restauré ensuite (ERREURS.md #017).
- Une donnée a **un** auteur. Ne jamais recopier une liste, une constante ou une règle
  dans une seconde fonction.
- La doc part dans le même commit que le code. Le code mort se supprime au passage.
