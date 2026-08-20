# mycounts

Application de gestion de budget de foyer : saisie des dépenses et des revenus, agenda
des prélèvements, plafonds par catégorie.

**Ce fichier décrit l'état RÉEL du projet.** S'il diverge du code, le code a raison et ce
fichier se corrige dans le même commit. Toute ligne ici doit pointer vers un fichier
existant : une ligne sans fichier est une intention, sa place est dans le plan ou dans
`BOUCLE.md`.

## État

**Livré** : authentification et foyer ; comptes privés ; catégories (créer, renommer,
retinter, archiver, supprimer — et **créer à la volée** depuis la saisie ou les budgets) ;
opérations (créer, modifier, supprimer, détailler) ; période budgétaire de paie à paie ;
soldes et liste ; amorçage avec solde d'ouverture ; récurrences, matérialisation
idempotente, calendrier mensuel et file « à confirmer » ; plafonds par catégorie avec leur
écran et les jauges de l'accueil ; virements ; page Épargne et détail d'un livret ;
correction du solde par ajustement ; enveloppes avec leurs réglages et la préparation
mensuelle ; statistiques et constats chiffrés ; import de relevé CSV avec écran de revue.
Interface Liquid Glass sur palette **bleu ardoise**, mobile d'abord, rail latéral au-delà
de 1024 px. Barre d'onglets à deux capsules (modèle Apple Music) ; écrans ouverts depuis
une bulle du haut, avec glissement de retour au doigt.

**Manque** : couverture des enveloppes par compte et déclaration de virement (lots E2 et
E4) ; onglet Foyer et comptes joints ; import de relevé au format PDF, non tranché ;
déploiement VPS.

Le plan d'exécution détaillé vit dans `docs/PLAN.md` — il fixe pour chaque écran ce qu'il
fait **et ce qu'il ne fait pas**. Cette seconde colonne existe parce que trois écrans ont
été refaits deux ou trois fois faute de l'avoir écrite avant de coder.

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
- **Un virement n'est ni une dépense ni un revenu** : l'argent change de poche sans
  quitter le foyer. Il reste dans les soldes des deux comptes, sort des dépenses et des
  plafonds.
- **Une classe utilitaire ne déclare rien que son consommateur puisse vouloir
  contredire** — deux incidents pour la même cause (ERREURS.md #008 et #020).
- **Une sonde de mesure a un domaine de validité** : le connaître avant de croire son
  verdict. Celle du contraste m'a trompé trois fois (#011, #021).
- **Frontend : `design/tokens.ts` est l'auteur unique de la palette ET de l'ordre
  d'empilement.** Les composants n'écrivent que `var(--…)`, y compris pour les `z-index` :
  ils choisissent un RÔLE (`--plan-feuille`, `--plan-ecran`…), jamais un nombre. Deux
  nombres choisis dans deux fichiers avaient rendu un formulaire invisible derrière l'écran
  qui l'ouvrait (ERREURS.md #038).
- **DA Liquid Glass sur palette bleu ardoise** — `#334155`, `#0EA5E9`, `#7DD3FC`,
  `#E0F2FE`, `#F1F5F9`. Un texte PEUT être posé sur du verre, à une condition mesurée —
  contraste AA de 4,5:1 vérifié dans les deux thèmes et les trois positions de transparence
  (`frontend/e2e/contraste.spec.ts`). Les opacités de texte et la teinte de l'accent sont
  donc contraintes par la mesure, pas choisies à l'œil : `#0EA5E9` ne porte AUCUN texte
  (2,77:1 avec du blanc) et s'assombrit même en thème clair pour tenir le seuil des
  composants graphiques.
- **Le contraste se mesure sur le RENDU, jamais sur un aplat.** Un montant n'est pas posé
  sur le fond mais sur le fond + le halo + le verre. Un calcul entre deux valeurs
  hexadécimales a pour domaine de validité « deux aplats opaques » — ce n'est pas cette
  interface. Trois erreurs pour cette seule cause (#011, #021, #035).
- **Mobile d'abord, bureau à part entière.** Media queries `min-width` uniquement. À
  partir de 1024 px la navigation devient un rail latéral — pas une tab bar centrée dans
  le vide.
- **Session en cookie `httponly` + `samesite=lax`**, jamais en `localStorage`. Une adresse
  inconnue et un mot de passe faux produisent la même réponse ET le même temps de réponse
  (empreinte-leurre Argon2 — sans elle, l'écart mesuré est de 12,5×).

## Garde-fous actifs

Onze — dix bloquants et un avertisseur — tous prouvés en les faisant échouer devant la faute qu'ils
prétendent détecter — **y compris les cibles du `Makefile` elles-mêmes** : `front-lint` a
été vert sans rien vérifier pendant toute la vie du projet, faute de `-p` sur un tsconfig
de références (ERREURS.md #034) : données bancaires (IBAN mod-97, PAN Luhn), secrets, dépendances LLM,
tête Alembic unique, flottants dans le domaine, requêtes hors repository, couleurs en dur
hors `tokens.ts`, et mise en page sur trois tailles d'écran. Le onzième avertit quand la base de
DÉMONSTRATION est en retard sur les migrations : elle se migre séparément, son API refuse
alors de démarrer, et l'application n'affiche plus rien (ERREURS.md #039). Chaque script documente en
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
