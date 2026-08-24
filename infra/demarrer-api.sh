#!/bin/sh
# Démarrage de l'API en production.
#
# Les migrations sont appliquées AVANT d'ouvrir le port : servir une requête contre un
# schéma en retard produit des erreurs que personne ne relie à un déploiement. Le
# garde-fou n°4 garantit une tête unique, donc « upgrade head » est déterministe.
set -eu

echo "Migrations : application de la tête Alembic…"
alembic upgrade head

echo "Démarrage d'uvicorn sur le port 8000…"
exec uvicorn mycounts.api.app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
