"""Dates civiles et bornes de période.

Auteur **unique** de la notion de « aujourd'hui » et de « ce mois-ci ». Recopier ce
calcul ailleurs, c'est garantir qu'un écran affichera un mois pendant qu'un autre en
calculera un différent.
"""

from __future__ import annotations

import datetime as dt
from typing import Final
from zoneinfo import ZoneInfo

FUSEAU: Final = ZoneInfo("Europe/Paris")
"""Fuseau de référence du foyer.

Une opération saisie à minuit le 31 appartient au mois du **31**, pas au suivant : la
date d'opération est une date civile en Europe/Paris, jamais une conversion d'UTC faite
par le navigateur. Le client n'a pas voix au chapitre — il n'envoie jamais « aujourd'hui ».
"""


def aujourd_hui(maintenant: dt.datetime | None = None) -> dt.date:
    """Date civile courante en Europe/Paris.

    `maintenant` n'existe que pour les tests : le code applicatif ne le passe jamais.
    """
    instant = maintenant or dt.datetime.now(tz=dt.UTC)
    if instant.tzinfo is None:
        raise ValueError("Un instant sans fuseau ne peut pas produire une date civile.")
    return instant.astimezone(FUSEAU).date()


def bornes_du_mois(jour: dt.date) -> tuple[dt.date, dt.date]:
    """Premier et dernier jour du mois **civil** contenant `jour`, bornes **incluses**.

    ATTENTION : ce n'est PAS la période budgétaire du foyer, qui va de paie à paie.
    Cette fonction sert aux usages calendaires (agenda, libellés de date). Le calcul des
    soldes et des plafonds utilisera la période budgétaire — voir BOUCLE.md, points
    ouverts. Ne pas se servir de celle-ci comme substitut : c'est précisément ainsi
    qu'un écran affiche un mois pendant qu'un autre en calcule un différent.

    Bornes incluses et non demi-ouvertes : les requêtes s'écrivent `BETWEEN`, et le
    dernier jour du mois est visible dans les logs — un intervalle `< 1er du mois
    suivant` se relit mal quand on cherche un écart.
    """
    debut = jour.replace(day=1)
    if debut.month == 12:
        premier_du_suivant = debut.replace(year=debut.year + 1, month=1)
    else:
        premier_du_suivant = debut.replace(month=debut.month + 1)
    return debut, premier_du_suivant - dt.timedelta(days=1)
