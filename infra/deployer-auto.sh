#!/usr/bin/env bash
# Garde-fou du déploiement automatique — appelé par `mycounts-deploy.timer`.
#
# Un timer branché directement sur `deployer.sh` ferait deux choses mal :
#   1. reconstruire deux images et redémarrer les services toutes les 5 minutes
#      même quand rien n'a changé ;
#   2. rejouer indéfiniment une branche cassée, en écrasant à chaque tour les
#      journaux qui permettraient de comprendre.
# D'où une comparaison de révision et une mémoire des échecs.
#
# Les deux piles ont chacune leur ARBRE DE TRAVAIL. Un dépôt unique ne peut pas
# être sur `main` et sur `dev` en même temps : partager l'arbre ferait déployer
# la préproduction avec le code de la production, ou l'inverse.
set -euo pipefail

declare -A ARBRES=(
    [prod]="$HOME/mycounts"
    [dev]="$HOME/mycounts-dev"
)
declare -A BRANCHES=(
    [prod]="main"
    [dev]="dev"
)

JOURNAL="$HOME/mycounts-deploy.log"
dire() { printf '%s  %s\n' "$(date '+%F %T')" "$*" >> "$JOURNAL"; }

for PILE in prod dev; do
    ARBRE="${ARBRES[$PILE]}"
    BRANCHE="${BRANCHES[$PILE]}"
    ECHEC="$HOME/.mycounts-deploy-echec-$PILE"

    [[ -d "$ARBRE/.git" ]] || continue          # pile pas encore installée
    [[ -f "$ARBRE/infra/.env.$PILE" ]] || continue

    git -C "$ARBRE" fetch origin "$BRANCHE" --quiet 2>/dev/null || {
        dire "[$PILE] récupération impossible (réseau ?)"
        continue
    }

    LOCAL=$(git -C "$ARBRE" rev-parse HEAD)
    DISTANT=$(git -C "$ARBRE" rev-parse "origin/$BRANCHE")
    [[ "$LOCAL" == "$DISTANT" ]] && continue    # rien de neuf : silence

    # Ce commit a déjà échoué : on ne le rejoue pas en boucle. On attend qu'un
    # nouveau commit arrive, c'est-à-dire qu'un humain ait corrigé quelque chose.
    if [[ -f "$ECHEC" ]] && [[ "$(cat "$ECHEC")" == "$DISTANT" ]]; then
        continue
    fi

    dire "[$PILE] ──────── ${LOCAL:0:7} → ${DISTANT:0:7}"
    if "$ARBRE/infra/deployer.sh" "$PILE" >> "$JOURNAL" 2>&1; then
        dire "[$PILE] ✓ déployé ${DISTANT:0:7}"
        rm -f "$ECHEC"
    else
        code=$?
        dire "[$PILE] ✗ ÉCHEC (code $code) sur ${DISTANT:0:7} — pas de nouvelle tentative avant un nouveau commit"
        echo "$DISTANT" > "$ECHEC"
    fi
done

# Le journal ne doit pas grossir sans fin sur une machine de production.
if [[ -f "$JOURNAL" ]] && [[ $(stat -c%s "$JOURNAL") -gt 5242880 ]]; then
    tail -n 2000 "$JOURNAL" > "$JOURNAL.tmp" && mv "$JOURNAL.tmp" "$JOURNAL"
    dire "journal tronqué à 2000 lignes"
fi
