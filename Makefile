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
	@# Avertit sans bloquer : voir la tête du script. Une base de démonstration absente
	@# ou injoignable n'est pas une faute, mais une démonstration EN RETARD produit une
	@# application qui n'affiche plus rien — piège documenté dans BOUCLE.md et payé quand
	@# même le 20 août 2026, faute d'un contrôle qui le dise.
	$(PY) -m scripts.verifier_demo_migree

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
	# Sans « --with-deps » : cette option lance un apt-get système qui, sur les runners
	# GitHub, est resté bloqué 40 minutes sans jamais rendre la main. Les bibliothèques
	# dont Chromium a besoin sont déjà présentes sur ubuntu-latest.
	cd frontend && npx playwright install chromium

front-lint:
	@# `-p` sur CHAQUE projet, et non `tsc --noEmit` nu. Le tsconfig.json racine est un
	@# fichier de références (`"files": []`) : sans `-p`, tsc n'a aucun fichier à compiler,
	@# annonce « No errors found » et sort en 0 quoi qu'il arrive. Ce contrôle a été vert
	@# pendant toute la vie du projet sans jamais rien vérifier — mesuré le 20 août 2026 en
	@# lui présentant une erreur de type que la forme `-p` rattrape et que celle-ci ratait.
	cd frontend && npx tsc --noEmit -p tsconfig.app.json
	cd frontend && npx tsc --noEmit -p tsconfig.node.json

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

# Base ET PORTS distincts pour la démonstration.
#
# La base séparée ne suffisait pas : Playwright est configuré avec
# « reuseExistingServer », donc les tests de bout en bout se branchaient sur le serveur
# de démonstration déjà lancé — et écrivaient dans SA base. Les ports doivent donc
# différer aussi, sans quoi les deux usages se retrouvent malgré tout.
URL_DEMO := postgresql+psycopg://mycounts:mycounts@localhost:5434/mycounts_demo
PORT_API_DEMO := 8011
PORT_WEB_DEMO := 5190

# Lance l'application pour un essai depuis un autre appareil.
#
# ATTENTION : pas de HTTPS. Sur Tailscale le tunnel est chiffré par WireGuard, donc le
# mot de passe ne circule pas en clair. Sur un Wi-Fi ordinaire, si.
demo: demo-migrer demo-arret
	@sleep 1
	@# --reload : sans lui, la démonstration continue de servir le code du jour où elle a
	@# été lancée. Vite recharge le frontend à chaud, pas uvicorn — d'où une interface à
	@# jour posée sur une API figée, et des « Not Found » sur des routes pourtant écrites.
	@# Voir ERREURS.md #022.
	@(MYCOUNTS_DATABASE_URL="$(URL_DEMO)" $(PY) -m uvicorn mycounts.api.app:app \
		--app-dir backend --port $(PORT_API_DEMO) --host 127.0.0.1 --reload \
		--reload-dir backend > /tmp/mycounts-api.log 2>&1 &)
	@(cd frontend && MYCOUNTS_PORT_WEB=$(PORT_WEB_DEMO) MYCOUNTS_PORT_API=$(PORT_API_DEMO) \
		npm run dev > /tmp/mycounts-web.log 2>&1 &)
	@sleep 4
	@echo ""
	@echo "  Sur cette machine   http://127.0.0.1:$(PORT_WEB_DEMO)"
	@echo "  Depuis un appareil  http://$$(tailscale ip -4 2>/dev/null || ipconfig getifaddr en0):$(PORT_WEB_DEMO)"
	@echo ""
	@echo "  Le backend n'écoute que sur 127.0.0.1 : seul le proxy l'atteint."
	@echo "  Base ET ports dédiés : les tests ne touchent pas à ces données."
	@echo "  Journaux : /tmp/mycounts-api.log et /tmp/mycounts-web.log"

# Applique les migrations sur la base de démonstration et s'assure qu'un compte existe.
demo-migrer:
	MYCOUNTS_DATABASE_URL="$(URL_DEMO)" .venv/bin/alembic upgrade head
	MYCOUNTS_DATABASE_URL="$(URL_DEMO)" \
		MYCOUNTS_MOT_DE_PASSE_INITIAL="$(MOT_DE_PASSE_E2E)" \
		$(PY) -m scripts.creer_premier_compte "Mon foyer" "$(COURRIEL_E2E)" "Olivier" \
		--ignorer-si-existe

demo-arret:
	@pkill -f "port $(PORT_API_DEMO)" 2>/dev/null || true
	@pkill -f "MYCOUNTS_PORT_WEB=$(PORT_WEB_DEMO)" 2>/dev/null || true
	@lsof -ti tcp:$(PORT_API_DEMO) 2>/dev/null | xargs kill 2>/dev/null || true
	@lsof -ti tcp:$(PORT_WEB_DEMO) 2>/dev/null | xargs kill 2>/dev/null || true
	@echo "Serveurs de démonstration arrêtés."

db-haut:
	docker compose up -d
	@until docker compose exec -T db pg_isready -U mycounts >/dev/null 2>&1; do sleep 1; done
	$(MAKE) migrer
	@echo "PostgreSQL sur le port 5434, migrations appliquées"

db-bas:
	docker compose down
