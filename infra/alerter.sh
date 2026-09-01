#!/usr/bin/env bash
# Alerte push vers le téléphone — le SEUL point de sortie des alertes d'exploitation.
#
#   infra/alerter.sh <pile> <cle> panne "<titre>" "<message>"   # signale un problème
#   infra/alerter.sh <pile> <cle> ok    "<titre>"               # signale son retour à la normale
#   infra/alerter.sh <pile> <cle> info  "<titre>" "<message>"   # message sans état (test, heartbeat)
#
# Une alerte est un CHANGEMENT D'ÉTAT, pas une mesure répétée. Un timer qui constate
# la même panne toutes les cinq minutes n'envoie qu'une notification : la première.
# La clé identifie le sujet (api, https, sauvegarde…) ; un état est retenu par
# pile et par clé dans ~/.mycounts-alertes/. « ok » n'envoie rien si aucune panne
# n'avait été signalée — le silence est l'état normal, et il doit le rester.
#
# Transport : ntfy (https://ntfy.sh ou une instance à soi). L'URL du sujet vit dans
# infra/.env.<pile> sous MYCOUNTS_ALERTE_URL — le nom du sujet fait office de secret,
# il ne se recopie nulle part ailleurs. URL absente : rien ne part, mais le journal
# le dit, pour qu'un silence ne soit jamais pris pour une santé parfaite.
#
# Ce qui ne passe JAMAIS par ici : un montant, un libellé d'opération, une adresse,
# un jeton. Les appelants n'envoient que des faits d'infrastructure.
set -euo pipefail

PILE="${1:-}"; CLE="${2:-}"; ETAT="${3:-}"; TITRE="${4:-}"; MESSAGE="${5:-}"
[[ -n "$PILE" && -n "$CLE" && -n "$ETAT" && -n "$TITRE" ]] \
    || { echo "usage: $0 <pile> <cle> <panne|ok|info> <titre> [message]" >&2; exit 2; }
case "$ETAT" in panne|ok|info) ;; *) echo "état inconnu : $ETAT" >&2; exit 2 ;; esac

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ETATS="$HOME/.mycounts-alertes"
FICHIER_ETAT="$ETATS/$PILE-$CLE"
JOURNAL="$HOME/mycounts-alertes.log"
mkdir -p "$ETATS"

dire() { printf '%s  [%s] %s\n' "$(date '+%F %T')" "$PILE" "$*" >> "$JOURNAL"; }

# Lecture d'UNE variable du fichier d'environnement, sans le sourcer : sourcer un
# fichier de secrets dans un script appelé par un timer en exporterait le contenu à
# tout ce que le script lance ensuite.
lire_env() {
    local fichier="$REPO/infra/.env.$PILE"
    [[ -f "$fichier" ]] || return 0
    sed -n "s/^$1=//p" "$fichier" | tail -1
}

envoyer() {
    local titre="$1" message="$2" priorite="$3" etiquettes="$4"
    local url
    url="$(lire_env MYCOUNTS_ALERTE_URL)"
    if [[ -z "$url" ]]; then
        dire "NON ENVOYÉ (MYCOUNTS_ALERTE_URL absente) : $titre — $message"
        return 0
    fi
    if curl -sS --max-time 10 -o /dev/null \
        -H "Title: $titre" -H "Priority: $priorite" -H "Tags: $etiquettes" \
        -d "$message" "$url"; then
        dire "envoyé : $titre — $message"
    else
        dire "ÉCHEC D'ENVOI : $titre — $message"
    fi
}

case "$ETAT" in
    panne)
        # Même panne, même message : déjà signalée, on se tait. Un message différent
        # sur la même clé (un autre commit en retard, un autre compteur) repart.
        if [[ -f "$FICHIER_ETAT" ]] && [[ "$(cat "$FICHIER_ETAT")" == "$MESSAGE" ]]; then
            exit 0
        fi
        printf '%s' "$MESSAGE" > "$FICHIER_ETAT"
        envoyer "[$PILE] $TITRE" "$MESSAGE" high warning
        ;;
    ok)
        [[ -f "$FICHIER_ETAT" ]] || exit 0
        rm -f "$FICHIER_ETAT"
        envoyer "[$PILE] $TITRE — rétabli" "${MESSAGE:-De nouveau normal.}" default white_check_mark
        ;;
    info)
        envoyer "[$PILE] $TITRE" "$MESSAGE" low information_source
        ;;
esac
