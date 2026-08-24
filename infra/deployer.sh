#!/usr/bin/env bash
# Déploiement d'UNE pile mycounts sur le VPS.
#
#   infra/deployer.sh prod              # déploie origin/main  sur mycounts.app
#   infra/deployer.sh dev               # déploie origin/dev   sur dev.mycounts.app
#   infra/deployer.sh prod --verifie    # ne fait que constater l'état
#
# Chaque pile a son arbre de travail, sa base et son verrou : déployer la
# préproduction ne doit jamais pouvoir toucher la production, même par erreur
# de frappe. Le verrou est pris ICI et non dans l'appelant — un verrou qui ne
# protège que le chemin du timer laisse passer les exécutions manuelles, faute
# constatée sur luminapp le 17 août 2026 (deux `alembic upgrade head`
# concurrents sur la même base).
set -euo pipefail

PILE="${1:-}"
case "$PILE" in
    prod) BRANCHE="main" ;;
    dev)  BRANCHE="dev" ;;
    *)    echo "usage: $0 <prod|dev> [--verifie]" >&2; exit 2 ;;
esac

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "$REPO/infra/docker-compose.vps.yml" --env-file "$REPO/infra/.env.$PILE")
SAUVEGARDES="$HOME/sauvegardes-mycounts"
VERROU="$HOME/.mycounts-deploy-$PILE.lock"
CONTENEUR_DB="mycounts-$PILE"_db

etape() { printf '\n── %s\n' "$*"; }
echec() { printf '\n✗ ÉCHEC : %s\n' "$*" >&2; exit 1; }

[[ -f "$REPO/infra/.env.$PILE" ]] || echec "infra/.env.$PILE absent — copier depuis infra/.env.example"

if [[ "${2:-}" != "--verifie" ]]; then
    exec 9>"$VERROU"
    flock -n 9 || echec "un déploiement $PILE est déjà en cours (verrou $VERROU)"
fi

if [[ "${2:-}" == "--verifie" ]]; then
    etape "État de la pile $PILE"
    git -C "$REPO" log --oneline -1
    "${COMPOSE[@]}" ps --format '{{.Name}}\t{{.Status}}'
    exit 0
fi

# ── 1. Sauvegarder la base ───────────────────────────────────────────────────
# En premier et sans condition : une migration ratée sans sauvegarde n'a pas de
# marche arrière. Une pile jamais démarrée n'a pas encore de base — ce n'est pas
# une erreur, mais tout autre échec en est une.
if docker ps --format '{{.Names}}' | grep -qx "$CONTENEUR_DB"; then
    etape "Sauvegarde de la base $PILE"
    HORODATAGE=$(date +%F-%H%M%S)
    mkdir -p "$SAUVEGARDES"
    ARCHIVE="$SAUVEGARDES/$PILE-$HORODATAGE.sql.gz"
    docker exec "$CONTENEUR_DB" pg_dump -U mycounts mycounts | gzip > "$ARCHIVE" \
        || echec "sauvegarde de la base $PILE"
    # Un fichier de quelques octets est une sauvegarde vide : mieux vaut refuser
    # d'avancer que croire un fichier qui ne contient rien.
    TAILLE=$(stat -c%s "$ARCHIVE")
    [[ "$TAILLE" -lt 512 ]] && echec "sauvegarde suspecte ($TAILLE octets) : $ARCHIVE"
    echo "  $ARCHIVE ($(numfmt --to=iec "$TAILLE"))"

    # Sept jours suffisent : au-delà, une sauvegarde d'un schéma périmé ne se
    # restaure plus sans travail, et elle remplit le disque en silence.
    find "$SAUVEGARDES" -name "$PILE-*.sql.gz" -mtime +7 -delete
else
    echo "Pile $PILE encore jamais démarrée : aucune base à sauvegarder."
fi

# ── 2. Récupérer le code ─────────────────────────────────────────────────────
etape "Mise à jour du code ($BRANCHE)"
AVANT=$(git -C "$REPO" rev-parse --short HEAD)
git -C "$REPO" fetch origin "$BRANCHE" --quiet || echec "récupération de origin/$BRANCHE"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] \
    || echec "l'arbre contient des modifications suivies locales ; refus de les écraser"
git -C "$REPO" merge-base --is-ancestor HEAD "origin/$BRANCHE" \
    || echec "la branche locale est en avance ou divergente ; pousser ou réconcilier d'abord"
git -C "$REPO" merge --ff-only "origin/$BRANCHE" --quiet \
    || echec "mise à jour non fast-forward"
APRES=$(git -C "$REPO" rev-parse --short HEAD)
if [[ "$AVANT" == "$APRES" ]]; then
    echo "  déjà sur $APRES — on reconstruit quand même"
else
    git -C "$REPO" log --oneline "$AVANT..$APRES" | sed 's/^/    /'
fi

# ── 3. Construire et démarrer ────────────────────────────────────────────────
etape "Construction des images"
"${COMPOSE[@]}" build api web || echec "construction"

# Les migrations sont jouées par le point d'entrée de l'API, avant qu'elle
# n'ouvre son port : inutile de les rejouer ici, et le faire ouvrirait une
# seconde porte sur la même chaîne Alembic.
etape "Redémarrage des services"
"${COMPOSE[@]}" up -d || echec "démarrage"

# ── 4. Attendre la santé RÉELLE ──────────────────────────────────────────────
# Un conteneur « démarré » n'est pas un service qui répond : sans cette attente,
# le déploiement se déclarerait réussi pendant qu'uvicorn échoue à joindre la
# base, et l'échec ne se verrait qu'à la première visite.
etape "Vérification de santé"
for _ in $(seq 1 40); do
    ETAT=$(docker inspect --format '{{.State.Health.Status}}' "mycounts-${PILE}_api" 2>/dev/null || echo absent)
    [[ "$ETAT" == "healthy" ]] && break
    sleep 3
done
[[ "$ETAT" == "healthy" ]] || {
    docker logs "mycounts-${PILE}_api" --tail 30 2>&1 | sed 's/^/    /'
    echec "l'API $PILE n'est pas saine après 2 minutes (état : $ETAT)"
}

echo
echo "✓ pile $PILE déployée en $APRES"
"${COMPOSE[@]}" ps --format '{{.Name}}\t{{.Status}}'
