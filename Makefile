# Auteur UNIQUE de la liste des contrôles. La CI appelle ces cibles : elle ne recopie
# jamais la liste, sinon les deux dérivent et l'une des deux ment.

PY := .venv/bin/python

.PHONY: aide installer lint types garde-fous tests tests-integration tests-e2e verifier migrer db-haut db-bas front-installer front-lint front-tests demo demo-arret

aide:
	@echo "make installer          Crée le venv et installe les dépendances"
	@echo "make verifier           Tout : lint, types, garde-fous, tests"
	@echo "make db-haut            Démarre PostgreSQL et applique les migrations"
	@echo "make tests-integration  Tests contre le vrai PostgreSQL"
	@echo "make tests-e2e          Mise en page sur 390 / 820 / 1280 px, dans un vrai navigateur"
	@echo "make front-tests        Tests unitaires du frontend"
	@echo "make demo               Lance l'app, accessible depuis tes autres appareils"
	@echo "make demo-arret         Arrête les serveurs de démonstration"

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

# Fonctions pures du frontend (formatage des montants). Les écrans relèvent des tests
# de bout en bout : ce qui se voit se vérifie dans un navigateur.
front-tests:
	cd frontend && npx vitest run

# Le compte de démonstration est créé par le globalSetup de Playwright, pas ici : la
# suite doit être lançable seule, sans dépendre d'une étape make exécutée avant.
tests-e2e: migrer
	cd frontend && MYCOUNTS_COURRIEL_TEST="$(COURRIEL_E2E)" \
		MYCOUNTS_MOT_DE_PASSE_TEST="$(MOT_DE_PASSE_E2E)" npx playwright test

# Idempotent : rejouable sans effet si la base est déjà à jour.
migrer:
	.venv/bin/alembic upgrade head

verifier: lint types garde-fous tests

# Lance l'application pour un essai depuis un autre appareil.
#
# ATTENTION, deux limites à connaître :
#  1. pas de HTTPS. Sur Tailscale le tunnel est chiffré par WireGuard, donc le mot de
#     passe ne circule pas en clair. Sur un Wi-Fi ordinaire, si.
#  2. c'est la base de DÉVELOPPEMENT. `make tests-integration` la vide (TRUNCATE) :
#     toute donnée saisie ici disparaîtra à la prochaine exécution des tests.
demo: migrer
	@pkill -f "uvicorn mycounts" 2>/dev/null || true
	@pkill -f "mycounts/frontend/node_modules/.bin/vite" 2>/dev/null || true
	@sleep 1
	@($(PY) -m uvicorn mycounts.api.app:app --app-dir backend --port 8010 \
		--host 127.0.0.1 > /tmp/mycounts-api.log 2>&1 &)
	@(cd frontend && npm run dev > /tmp/mycounts-web.log 2>&1 &)
	@sleep 4
	@echo ""
	@echo "  Sur cette machine   http://127.0.0.1:5189"
	@echo "  Depuis un appareil  http://$$(tailscale ip -4 2>/dev/null || ipconfig getifaddr en0):5189"
	@echo ""
	@echo "  Le backend n'écoute que sur 127.0.0.1 : seul le proxy l'atteint."
	@echo "  Journaux : /tmp/mycounts-api.log et /tmp/mycounts-web.log"

demo-arret:
	@pkill -f "uvicorn mycounts" 2>/dev/null || true
	@pkill -f "mycounts/frontend/node_modules/.bin/vite" 2>/dev/null || true
	@echo "Serveurs de démonstration arrêtés."

db-haut:
	docker compose up -d
	@until docker compose exec -T db pg_isready -U mycounts >/dev/null 2>&1; do sleep 1; done
	$(MAKE) migrer
	@echo "PostgreSQL sur le port 5434, migrations appliquées"

db-bas:
	docker compose down
