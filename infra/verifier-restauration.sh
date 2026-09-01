#!/usr/bin/env bash
# Restaure la dernière sauvegarde d'une pile dans une base JETABLE et compare.
#
#   infra/verifier-restauration.sh <prod|dev> [archive]
#
# Une sauvegarde ne vaut que ce qu'on en restaure. Ce script rejoue la dernière
# archive dans une base « mycounts_restauration » du MÊME conteneur PostgreSQL, puis
# compare cinq grandeurs entre la base vivante et la base restaurée : la révision
# Alembic, le nombre d'opérations, la somme de leurs montants en centimes, le nombre
# de comptes et le nombre d'identités. Si l'une diffère, il échoue.
#
# Domaine de validité : la comparaison suppose qu'aucune écriture n'a eu lieu entre
# la sauvegarde et la restauration. Lancé à 4 h du matin, c'est vrai ; lancé pendant
# qu'on saisit une dépense, il peut rougir à tort — et un faux rouge se relit, un
# faux vert non. La base jetable est détruite quoi qu'il arrive.
set -euo pipefail

PILE="${1:-}"
case "$PILE" in prod|dev) ;; *) echo "usage: $0 <prod|dev> [archive]" >&2; exit 2 ;; esac

SAUVEGARDES="$HOME/sauvegardes-mycounts"
CONTENEUR_DB="mycounts-${PILE}_db"
BASE_JETABLE="mycounts_restauration"
ARCHIVE="${2:-$(ls -t "$SAUVEGARDES/$PILE"-*.sql.gz 2>/dev/null | head -1)}"
[[ -n "$ARCHIVE" && -f "$ARCHIVE" ]] || { echo "aucune archive $PILE à restaurer" >&2; exit 1; }

psql_sur() { docker exec -i "$CONTENEUR_DB" psql -U mycounts -d "$1" -Atq -v ON_ERROR_STOP=1 "${@:2}"; }

nettoyer() {
    docker exec "$CONTENEUR_DB" dropdb -U mycounts --if-exists "$BASE_JETABLE" >/dev/null 2>&1 || true
}
trap nettoyer EXIT
nettoyer

docker exec "$CONTENEUR_DB" createdb -U mycounts "$BASE_JETABLE"
gunzip -c "$ARCHIVE" | psql_sur "$BASE_JETABLE" >/dev/null

# Cinq grandeurs, choisies pour qu'une restauration partielle en fasse bouger une :
# une table absente change un compte, une ligne perdue change la somme des centimes.
MESURE='select (select version_num from alembic_version)
     || chr(124) || (select count(*) from operation)
     || chr(124) || (select coalesce(sum(montant_centimes), 0) from operation)
     || chr(124) || (select count(*) from compte)
     || chr(124) || (select count(*) from utilisateur)'
VIVANTE=$(printf '%s' "$MESURE" | psql_sur mycounts)
RESTAUREE=$(printf '%s' "$MESURE" | psql_sur "$BASE_JETABLE")

if [[ "$VIVANTE" != "$RESTAUREE" ]]; then
    echo "restauration DIVERGENTE pour $ARCHIVE" >&2
    echo "  vivante   : $VIVANTE" >&2
    echo "  restaurée : $RESTAUREE" >&2
    exit 1
fi
echo "restauration vérifiée : $(basename "$ARCHIVE") — révision|opérations|centimes|comptes|identités = $RESTAUREE"
