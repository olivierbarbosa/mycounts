#!/usr/bin/env bash
# Installe (ou met à jour) les unités systemd de mycounts sur le VPS.
#
#   sudo infra/installer-timers.sh
#
# Les unités vivent dans infra/systemd/ : le dépôt est leur auteur, /etc n'en est
# qu'une copie. Idempotent — relançable après chaque changement d'unité.
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "à lancer avec sudo" >&2; exit 2; }
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/systemd" && pwd)"

for unite in "$SOURCE"/*.service "$SOURCE"/*.timer; do
    install -m 0644 "$unite" "/etc/systemd/system/$(basename "$unite")"
done
systemctl daemon-reload
for timer in mycounts-deploy mycounts-surveiller mycounts-sauvegarde; do
    systemctl enable --now "$timer.timer"
done
systemctl list-timers --all | grep mycounts
