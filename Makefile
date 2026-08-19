# Auteur UNIQUE de la liste des contrôles. La CI appelle ces cibles : elle ne recopie
# jamais la liste, sinon les deux dérivent et l'une des deux ment.

PY := .venv/bin/python

.PHONY: aide installer lint types garde-fous tests tests-integration verifier migrer db-haut db-bas

aide:
	@echo "make installer          Crée le venv et installe les dépendances"
	@echo "make verifier           Tout : lint, types, garde-fous, tests"
	@echo "make db-haut            Démarre PostgreSQL et applique les migrations"
	@echo "make tests-integration  Tests contre le vrai PostgreSQL"

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

tests:
	$(PY) -m pytest tests/unit -q

tests-integration:
	$(PY) -m pytest tests/integration -q

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
