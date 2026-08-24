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
PROXY_FIABLE_HOTE="${MYCOUNTS_PROXY_FIABLE_HOTE:-luminapp_traefik}"
PROXY_FIABLE_IP="$(getent hosts "$PROXY_FIABLE_HOTE" | sed -n '1s/ .*//p')"
if [ -z "$PROXY_FIABLE_IP" ]; then
    echo "Proxy fiable introuvable : $PROXY_FIABLE_HOTE" >&2
    exit 1
fi
echo "En-têtes de proxy acceptés uniquement depuis $PROXY_FIABLE_HOTE ($PROXY_FIABLE_IP)."
exec uvicorn mycounts.api.app:app --host 0.0.0.0 --port 8000 \
    --proxy-headers --forwarded-allow-ips="$PROXY_FIABLE_IP"
