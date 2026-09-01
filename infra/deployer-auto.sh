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

    # Ce qui TOURNE, pas ce que l'arbre contient. Comparer `HEAD` à `origin` laissait
    # une panne muette : le 24 août 2026, l'arbre a été avancé de dix commits à la main
    # sans déploiement, si bien que `HEAD == origin` concluait « rien de neuf » pendant
    # que la production servait toujours 808930c. L'arbre dit l'intention, l'étiquette
    # de l'image dit le fait — seul le fait décide d'un déploiement.
    DEPLOYEE=$(docker inspect --format \
        '{{index .Config.Labels "org.opencontainers.image.revision"}}' \
        "mycounts-${PILE}_api" 2>/dev/null || true)
    DEPLOYEE=${DEPLOYEE:-aucune}
    [[ "$DEPLOYEE" == "$DISTANT" ]] && continue    # déjà en ligne : silence

    # Cet arbre peut aussi servir ponctuellement à une intervention locale. Un ancien
    # comportement appelait alors `deployer.sh`, qui remettait brutalement l'arbre sur
    # origin/$BRANCHE et effaçait les commits non poussés. Le déploiement automatique ne
    # possède pas ce droit : il n'avance que par fast-forward depuis un arbre propre.
    if [[ -n "$(git -C "$ARBRE" status --porcelain)" ]]; then
        dire "[$PILE] arbre suivi modifié localement — déploiement différé"
        continue
    fi
    if ! git -C "$ARBRE" merge-base --is-ancestor "$LOCAL" "$DISTANT"; then
        dire "[$PILE] branche locale en avance ou divergente — déploiement différé"
        continue
    fi

    # Ce commit a déjà échoué : on ne le rejoue pas en boucle. On attend qu'un
    # nouveau commit arrive — ou que six heures passent. Sans ce délai, une panne
    # PASSAGÈRE condamnait le commit pour toujours : la préproduction est restée
    # bloquée six jours sur un jeton Docker Hub refusé une seule fois (27 août 2026),
    # et rien ne le disait. Le fichier porte le SHA et l'instant de l'échec.
    if [[ -f "$ECHEC" ]] && [[ "$(cut -d' ' -f1 "$ECHEC")" == "$DISTANT" ]]; then
        INSTANT_ECHEC=$(cut -d' ' -f2 "$ECHEC")
        DEPUIS=$(( $(date +%s) - ${INSTANT_ECHEC:-0} ))
        (( DEPUIS < 6 * 3600 )) && continue
        dire "[$PILE] nouvel essai de ${DISTANT:0:7} après $(( DEPUIS / 3600 )) h"
    fi

    # Le commit exact doit avoir passé le job GitHub Actions `verifier`. Un statut en
    # cours n'est PAS un échec : le prochain tick le relira. Une API GitHub indisponible
    # bloque le déploiement par sûreté, sans condamner le commit.
    if ! ETAT_CI=$(gh api "/repos/olivierbarbosa/mycounts/commits/$DISTANT/check-runs" \
        --jq '[.check_runs[] | select(.name == "verifier")] as $r | if ($r | length) == 0 or any($r[]; .status != "completed") then "attente" elif any($r[]; .conclusion == "success") then "succes" else "echec" end' \
        2>/dev/null); then
        dire "[$PILE] statut CI inaccessible — déploiement différé"
        continue
    fi
    case "$ETAT_CI" in
        succes) ;;
        attente)
            dire "[$PILE] CI encore en cours pour ${DISTANT:0:7} — déploiement différé"
            continue
            ;;
        *)
            dire "[$PILE] CI en échec pour ${DISTANT:0:7} — commit refusé"
            echo "$DISTANT $(date +%s)" > "$ECHEC"
            "$ARBRE/infra/alerter.sh" "$PILE" deploiement panne "CI rouge" \
                "Le commit ${DISTANT:0:7} a échoué en CI : il ne sera pas déployé."
            continue
            ;;
    esac

    dire "[$PILE] ──────── ${DEPLOYEE:0:7} → ${DISTANT:0:7}"
    if "$ARBRE/infra/deployer.sh" "$PILE" >> "$JOURNAL" 2>&1; then
        dire "[$PILE] ✓ déployé ${DISTANT:0:7}"
        rm -f "$ECHEC"
        "$ARBRE/infra/alerter.sh" "$PILE" deploiement ok "Déploiement" "${DISTANT:0:7} est en ligne."
    else
        code=$?
        dire "[$PILE] ✗ ÉCHEC (code $code) sur ${DISTANT:0:7} — nouvel essai dans six heures, ou au prochain commit"
        echo "$DISTANT $(date +%s)" > "$ECHEC"
        "$ARBRE/infra/alerter.sh" "$PILE" deploiement panne "Déploiement en échec" \
            "Le commit ${DISTANT:0:7} n'a pas pu être déployé (code $code). Voir ~/mycounts-deploy.log."
    fi
done

# Le journal ne doit pas grossir sans fin sur une machine de production.
if [[ -f "$JOURNAL" ]] && [[ $(stat -c%s "$JOURNAL") -gt 5242880 ]]; then
    tail -n 2000 "$JOURNAL" > "$JOURNAL.tmp" && mv "$JOURNAL.tmp" "$JOURNAL"
    dire "journal tronqué à 2000 lignes"
fi
