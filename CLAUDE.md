# mycounts

Application de gestion de budget de foyer : saisie des dépenses et des revenus, agenda
des prélèvements, plafonds par catégorie.

**Ce fichier décrit l'état RÉEL du projet.** S'il diverge du code, le code a raison et ce
fichier se corrige dans le même commit. Toute ligne ici doit pointer vers un fichier
existant : une ligne sans fichier est une intention, sa place est dans le plan ou dans
`BOUCLE.md`.

## État : lot 0 (socle) terminé

Il n'existe **aucune table métier, aucune migration, aucune authentification, aucun
écran**. Ce qui existe : les primitives de domaine, les garde-fous et l'outillage.

## Stack

Python 3.12 · FastAPI · PostgreSQL 16 · SQLAlchemy 2 · Alembic. Frontend React à venir
(lot 1). Tout est en français : noms de fonctions, de variables et de tests.

## Commandes

```bash
make installer          # venv + dépendances
make db-haut            # PostgreSQL sur le port 5434 (5433 est pris par un autre projet)
make verifier           # lint + types + garde-fous + tests unitaires
make tests-integration  # tests contre le vrai PostgreSQL
```

La liste des contrôles vit dans le `Makefile` et nulle part ailleurs ; la CI l'appelle.

## Règles en vigueur

- **Un montant est un entier de centimes** — `Cents` dans `backend/mycounts/domain/montants.py`.
  Aucun flottant dans `domain/`, vérifié par `scripts/verifier_pas_de_float.py`.
- **Les dates civiles sont en Europe/Paris** — `backend/mycounts/domain/calendrier.py`.
  En SQL, toujours `AT TIME ZONE 'Europe/Paris'`, jamais `::date` nu : le cast nu dépend
  du fuseau de session du serveur (mesuré, voir `tests/integration/test_socle_base.py`).
- **`bornes_du_mois()` est le mois CIVIL**, pas la période budgétaire. La période du foyer
  ira de paie à paie (lot 2). Ne pas confondre les deux.
- **Toute requête passera par `backend/mycounts/repository/`** — `scripts/verifier_scope_repository.py`
  refuse déjà tout `select`/`execute` écrit ailleurs dans `backend/mycounts/`.

## Garde-fous actifs

Six, tous bloquants, tous prouvés par un témoin dans `tests/unit/test_garde_fous.py` :
données bancaires (IBAN mod-97, PAN Luhn), secrets, dépendances LLM, tête Alembic unique,
flottants dans le domaine, requêtes hors repository. Chaque script documente en tête **ce
qu'il ne détecte pas** — lire cette section avant de lui faire confiance.

## Habitudes

- Une mesure qui ne peut pas rendre la réponse inverse ne prouve rien. Avant d'accepter un
  test ou un chiffre : *dans quel cas aurait-il donné l'autre résultat ?* Si la réponse est
  « aucun », l'exécuter contre l'implémentation fautive.
- Valider par le chemin de production : PostgreSQL réel, pas SQLite ; l'écran, pas `curl`.
- `ERREURS.md` se relit avant de toucher une zone où je me suis déjà trompé. Les trois
  entrées actuelles ont la même forme : *une vérification qui ne consulte que sa propre
  source*.
- Une donnée a **un** auteur. Ne jamais recopier une liste, une constante ou une règle
  dans une seconde fonction.
- La doc part dans le même commit que le code. Le code mort se supprime au passage.
