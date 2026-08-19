# Auteur UNIQUE de la liste des contrôles. La CI appelle ces cibles : elle ne recopie
# jamais la liste, sinon les deux dérivent et l'une des deux ment.

PY := .venv/bin/python

.PHONY: aide installer lint types garde-fous tests tests-integration tests-e2e verifier migrer db-haut db-bas front-installer front-lint

aide:
	@echo "make installer          Crée le venv et installe les dépendances"
	@echo "make verifier           Tout : lint, types, garde-fous, tests"
	@echo "make db-haut            Démarre PostgreSQL et applique les migrations"
	@echo "make tests-integration  Tests contre le vrai PostgreSQL"
	@echo "make tests-e2e          Mise en page sur 390 / 820 / 1280 px, dans un vrai navigateur"

installer:
	python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -e ".[dev]"

lint:
	$(PY) -m ruff check .

types:
	$(PY) -m mypy

garde-fous:
	$(PY) -m scripts.verifier_donnees_bancaires
	$(PY) -m scripts.verifier_secrets
	$(PY) -m scripts.verifier_dependances_llm
	$(PY) -m scripts.verifier_tete_alembic
	$(PY) -m scripts.verifier_pas_de_float
	$(PY) -m scripts.verifier_scope_repository
	$(PY) -m scripts.verifier_couleurs

tests:
	$(PY) -m pytest tests/unit -q

tests-integration:
	$(PY) -m pytest tests/integration -q

# Compte de démonstration des tests de bout en bout. Ce n'est PAS un compte de
# production : il n'existe que dans la base locale ou celle de la CI.
# Domaine ordinaire et non enregistré : « .test » est un TLD réservé que la validation
# d'adresse refuse — c'est justement ce qui a révélé l'incohérence d'ERREURS.md #009.
COURRIEL_E2E := essai@mycounts-demo.fr
MOT_DE_PASSE_E2E := correct cheval batterie agrafe

front-installer:
	cd frontend && npm ci --silent
	cd frontend && npx playwright install --with-deps chromium

front-lint:
	cd frontend && npx tsc --noEmit

# Le compte de démonstration est créé par le globalSetup de Playwright, pas ici : la
# suite doit être lançable seule, sans dépendre d'une étape make exécutée avant.
tests-e2e: migrer
	cd frontend && MYCOUNTS_COURRIEL_TEST="$(COURRIEL_E2E)" \
		MYCOUNTS_MOT_DE_PASSE_TEST="$(MOT_DE_PASSE_E2E)" npx playwright test

# Idempotent : rejouable sans effet si la base est déjà à jour.
migrer:
	.venv/bin/alembic upgrade head

verifier: lint types garde-fous tests

db-haut:
	docker compose up -d
	@until docker compose exec -T db pg_isready -U mycounts >/dev/null 2>&1; do sleep 1; done
	$(MAKE) migrer
	@echo "PostgreSQL sur le port 5434, migrations appliquées"

db-bas:
	docker compose down
