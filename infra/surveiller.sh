#!/usr/bin/env bash
# Surveillance des piles mycounts — appelée toutes les 5 minutes par mycounts-surveiller.timer.
#
# Chaque contrôle se termine par un appel à alerter.sh en « panne » ou en « ok » :
# c'est lui qui décide d'envoyer ou de se taire. Ce script MESURE, il n'a pas d'avis.
#
# Ce qu'il mesure, par pile :
#   api          — l'état de santé Docker de l'API (la sonde interroge /health, donc PostgreSQL)
#   courriels    — l'état de santé du worker SMTP (battement de cœur, cf. le compose)
#   file         — un courriel en attente depuis plus d'une heure : le worker ne traite pas
#   https        — la page d'accueil répond en 200 par Traefik, certificat compris
#   retard       — la révision qui TOURNE diffère d'origin/<branche> depuis plus d'une heure
#   sauvegarde   — la dernière sauvegarde vérifiée date de plus de 26 heures
#   erreurs-5xx  — des réponses 5xx dans les cinq dernières minutes
# Et une fois pour la machine : le disque au-delà de 85 %.
#
# Le lundi à 8 h (heure de Paris), un message « surveillance vivante » part quoi qu'il
# arrive : c'est le seul moyen de savoir que le canal d'alerte lui-même fonctionne.
#
# Ce qu'il ne mesure PAS : la justesse d'un solde, la présence d'un utilisateur, la
# lenteur d'une page. Aucune donnée financière n'est lue.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALERTER="$REPO/infra/alerter.sh"
ETATS="$HOME/.mycounts-alertes"
mkdir -p "$ETATS"

declare -A ARBRES=([prod]="$HOME/mycounts" [dev]="$HOME/mycounts-dev")
declare -A BRANCHES=([prod]="main" [dev]="dev")

lire_env() { sed -n "s/^$2=//p" "${ARBRES[$1]}/infra/.env.$1" 2>/dev/null | tail -1; }
sante() { docker inspect --format '{{.State.Health.Status}}' "$1" 2>/dev/null || echo absent; }

for PILE in prod dev; do
    ARBRE="${ARBRES[$PILE]}"
    [[ -f "$ARBRE/infra/.env.$PILE" ]] || continue
    API="mycounts-${PILE}_api"; DB="mycounts-${PILE}_db"; COURRIELS="mycounts-${PILE}_courriels"
    DOMAINE="$(lire_env "$PILE" MYCOUNTS_DOMAINE)"

    # ── api ──────────────────────────────────────────────────────────────────
    ETAT=$(sante "$API")
    if [[ "$ETAT" == "healthy" ]]; then
        "$ALERTER" "$PILE" api ok "API"
    else
        "$ALERTER" "$PILE" api panne "API hors service" "Conteneur $API : $ETAT."
    fi

    # ── courriels ────────────────────────────────────────────────────────────
    ETAT=$(sante "$COURRIELS")
    if [[ "$ETAT" == "healthy" ]]; then
        "$ALERTER" "$PILE" courriels ok "Worker de courriels"
    else
        "$ALERTER" "$PILE" courriels panne "Worker de courriels arrêté" "Conteneur $COURRIELS : $ETAT."
    fi

    # ── file de courriels ────────────────────────────────────────────────────
    # Un message en attente depuis une heure, c'est un mot de passe oublié que
    # personne ne reçoit. Comptage seul : ni destinataire, ni contenu.
    EN_ATTENTE=$(docker exec "$DB" psql -U mycounts -d mycounts -Atc \
        "select count(*) from courriel_sortant where envoye_le is null and cree_le < now() - interval '1 hour'" \
        2>/dev/null || echo "?")
    if [[ "$EN_ATTENTE" == "0" ]]; then
        "$ALERTER" "$PILE" file ok "File de courriels"
    else
        "$ALERTER" "$PILE" file panne "Courriels non envoyés" \
            "$EN_ATTENTE courriel(s) en attente depuis plus d'une heure. SMTP configuré ? Worker vivant ?"
    fi

    # ── https ────────────────────────────────────────────────────────────────
    if [[ -n "$DOMAINE" ]]; then
        CODE=$(curl -sS -o /dev/null --max-time 15 -w '%{http_code}' "https://$DOMAINE/" 2>/dev/null || echo 000)
        if [[ "$CODE" == "200" ]]; then
            "$ALERTER" "$PILE" https ok "Site"
        else
            "$ALERTER" "$PILE" https panne "Site injoignable" "https://$DOMAINE/ répond $CODE."
        fi
    fi

    # ── retard de déploiement ────────────────────────────────────────────────
    # deployer-auto.sh a déjà fait le fetch : on lit origin/<branche> sans le refaire.
    DISTANT=$(git -C "$ARBRE" rev-parse "origin/${BRANCHES[$PILE]}" 2>/dev/null || true)
    DEPLOYEE=$(docker inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$API" 2>/dev/null || true)
    RETARD="$ETATS/retard-$PILE"
    if [[ -n "$DISTANT" && "$DISTANT" == "$DEPLOYEE" ]]; then
        rm -f "$RETARD"
        "$ALERTER" "$PILE" retard ok "Déploiement"
    else
        [[ -f "$RETARD" && "$(cut -d' ' -f1 "$RETARD")" == "$DISTANT" ]] || echo "$DISTANT $(date +%s)" > "$RETARD"
        DEPUIS=$(( $(date +%s) - $(cut -d' ' -f2 "$RETARD") ))
        if (( DEPUIS > 3600 )); then
            "$ALERTER" "$PILE" retard panne "Production en retard" \
                "En ligne : ${DEPLOYEE:0:7}, attendu : ${DISTANT:0:7}, depuis $(( DEPUIS / 60 )) min. Voir ~/mycounts-deploy.log."
        fi
    fi

    # ── sauvegarde ───────────────────────────────────────────────────────────
    TRACE="$ETATS/sauvegarde-ok-$PILE"
    AGE=$(( $(date +%s) - $(cat "$TRACE" 2>/dev/null || echo 0) ))
    if (( AGE > 26 * 3600 )); then
        "$ALERTER" "$PILE" sauvegarde-age panne "Sauvegarde en retard" \
            "Aucune sauvegarde vérifiée depuis $(( AGE / 3600 )) h."
    else
        "$ALERTER" "$PILE" sauvegarde-age ok "Sauvegarde"
    fi

    # ── erreurs 5xx ──────────────────────────────────────────────────────────
    ERREURS=$(docker logs --since 5m "$API" 2>&1 | grep -cE '" 5[0-9]{2} ' || true)
    if [[ "$ERREURS" == "0" ]]; then
        "$ALERTER" "$PILE" erreurs-5xx ok "Erreurs serveur"
    else
        "$ALERTER" "$PILE" erreurs-5xx panne "Erreurs serveur" \
            "$ERREURS réponse(s) 5xx en cinq minutes. docker logs $API --since 10m"
    fi
done

# ── disque (une fois, rattaché à prod) ───────────────────────────────────────
if [[ -f "${ARBRES[prod]}/infra/.env.prod" ]]; then
    USAGE=$(df --output=pcent / | tail -1 | tr -dc '0-9')
    if (( USAGE > 85 )); then
        "$ALERTER" prod disque panne "Disque presque plein" "$USAGE % utilisés sur /."
    else
        "$ALERTER" prod disque ok "Disque"
    fi

    # ── battement hebdomadaire ───────────────────────────────────────────────
    SEMAINE=$(TZ=Europe/Paris date +%G-W%V)
    if [[ "$(TZ=Europe/Paris date +%u%H)" == "108" ]] \
        && [[ "$(cat "$ETATS/battement" 2>/dev/null)" != "$SEMAINE" ]]; then
        echo "$SEMAINE" > "$ETATS/battement"
        "$ALERTER" prod battement info "Surveillance vivante" \
            "Semaine $SEMAINE : la surveillance tourne. Pannes en cours : $(ls "$ETATS" | grep -cvE '^(retard-|sauvegarde-ok-|battement)' || true)."
    fi
fi
