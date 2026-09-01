#!/usr/bin/env bash
# Sauvegarde de la base d'UNE pile — auteur unique du pg_dump.
#
#   infra/sauvegarder.sh <prod|dev>        # écrit ~/sauvegardes-mycounts/<pile>-<horodatage>.sql.gz
#
# Appelé par deployer.sh avant chaque migration et par le timer quotidien. Un seul
# script pour les deux : deux copies du même pg_dump auraient dérivé, et l'une des
# deux aurait fini par produire une archive que l'autre ne sait pas relire.
#
# La restauration est vérifiée à part (verifier-restauration.sh) : une archive dont
# on n'a jamais rien restauré n'est pas une sauvegarde, c'est un fichier.
#
# Rétention : quatorze jours, sur le VPS lui-même (décidé le 2 septembre 2026, pas de
# copie hors site pour l'instant). Une perte du disque emporte donc la base ET ses
# sauvegardes — c'est la limite connue de ce script.
set -euo pipefail

PILE="${1:-}"
case "$PILE" in prod|dev) ;; *) echo "usage: $0 <prod|dev>" >&2; exit 2 ;; esac

SAUVEGARDES="$HOME/sauvegardes-mycounts"
CONTENEUR_DB="mycounts-${PILE}_db"
RETENTION_JOURS=14

docker ps --format '{{.Names}}' | grep -qx "$CONTENEUR_DB" \
    || { echo "conteneur $CONTENEUR_DB absent : rien à sauvegarder" >&2; exit 1; }

mkdir -p "$SAUVEGARDES"
ARCHIVE="$SAUVEGARDES/$PILE-$(date +%F-%H%M%S).sql.gz"
docker exec "$CONTENEUR_DB" pg_dump -U mycounts mycounts | gzip > "$ARCHIVE"

# Un fichier de quelques octets est une sauvegarde vide : mieux vaut refuser d'avancer
# que croire un fichier qui ne contient rien.
TAILLE=$(stat -c%s "$ARCHIVE")
if [[ "$TAILLE" -lt 512 ]]; then
    rm -f "$ARCHIVE"
    echo "sauvegarde suspecte ($TAILLE octets), archive supprimée" >&2
    exit 1
fi

find "$SAUVEGARDES" -name "$PILE-*.sql.gz" -mtime +"$RETENTION_JOURS" -delete
echo "$ARCHIVE"
