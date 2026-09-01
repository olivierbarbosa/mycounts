#!/usr/bin/env bash
# Sauvegarde quotidienne de chaque pile installée, restauration vérifiée dans la foulée.
# Appelé par mycounts-sauvegarde.timer, à 4 h UTC — l'heure où personne ne saisit.
#
# Le résultat laisse une TRACE DATÉE (~/.mycounts-alertes/sauvegarde-ok-<pile>) : la
# surveillance alerte si cette trace a plus de 26 heures. Sans elle, un timer mort
# serait indiscernable d'un timer qui réussit en silence (ERREURS.md #041).
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JOURNAL="$HOME/mycounts-sauvegarde.log"
mkdir -p "$HOME/.mycounts-alertes"
dire() { printf '%s  %s\n' "$(date '+%F %T')" "$*" >> "$JOURNAL"; }

for PILE in prod dev; do
    docker ps --format '{{.Names}}' | grep -qx "mycounts-${PILE}_db" || continue
    if ARCHIVE=$("$REPO/infra/sauvegarder.sh" "$PILE" 2>>"$JOURNAL") \
        && VERDICT=$("$REPO/infra/verifier-restauration.sh" "$PILE" "$ARCHIVE" 2>>"$JOURNAL"); then
        dire "[$PILE] $VERDICT"
        date +%s > "$HOME/.mycounts-alertes/sauvegarde-ok-$PILE"
        "$REPO/infra/alerter.sh" "$PILE" sauvegarde ok "Sauvegarde" "Sauvegarde et restauration vérifiées."
    else
        dire "[$PILE] ✗ sauvegarde ou restauration en échec"
        "$REPO/infra/alerter.sh" "$PILE" sauvegarde panne "Sauvegarde en échec" \
            "Sauvegarde ou restauration vérifiée en échec le $(date +%F). Voir ~/mycounts-sauvegarde.log."
    fi
done

if [[ -f "$JOURNAL" ]] && [[ $(stat -c%s "$JOURNAL") -gt 1048576 ]]; then
    tail -n 500 "$JOURNAL" > "$JOURNAL.tmp" && mv "$JOURNAL.tmp" "$JOURNAL"
fi
