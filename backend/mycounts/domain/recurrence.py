"""Échéances d'une opération récurrente.

**Auteur unique** du calcul « quelles dates tombe cette récurrence ».

Une règle décide de tout le reste : chaque échéance se calcule **depuis la date
d'ancrage**, jamais depuis l'échéance précédente. Une récurrence au 31 glisse au 28 en
février ; si le mois suivant repartait de ce 28, elle resterait au 28 pour toujours et
finirait par ne plus correspondre au prélèvement réel. C'est une dérive silencieuse : rien
ne la signale, et elle ne se voit qu'après plusieurs mois.
"""

from __future__ import annotations

import calendar
import datetime as dt
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum


class UniteRecurrence(StrEnum):
    JOUR = "jour"
    SEMAINE = "semaine"
    MOIS = "mois"
    AN = "an"


@dataclass(frozen=True)
class Cadence:
    """Rythme d'une récurrence : « tous les `intervalle` `unite` »."""

    unite: UniteRecurrence
    intervalle: int = 1

    def __post_init__(self) -> None:
        if self.intervalle < 1:
            raise ValueError("L'intervalle d'une récurrence vaut au moins 1.")


def _decaler_mois(ancre: dt.date, mois: int) -> dt.date:
    """Décale de `mois` mois depuis l'ancre, en rabattant au dernier jour existant.

    Le 31 janvier + 1 mois donne le 28 (ou 29) février, puis + 2 mois donne le 31 mars :
    le quantième d'origine est retrouvé dès que le mois le permet, parce que le calcul
    part toujours de l'ancre.
    """
    total = ancre.month - 1 + mois
    annee = ancre.year + total // 12
    numero_mois = total % 12 + 1
    dernier = calendar.monthrange(annee, numero_mois)[1]
    return dt.date(annee, numero_mois, min(ancre.day, dernier))


def echeance(ancre: dt.date, cadence: Cadence, rang: int) -> dt.date:
    """Date de la `rang`-ième occurrence (rang 0 = l'ancre elle-même)."""
    if rang < 0:
        raise ValueError("Le rang d'une échéance ne peut pas être négatif.")
    pas = cadence.intervalle * rang
    match cadence.unite:
        case UniteRecurrence.JOUR:
            return ancre + dt.timedelta(days=pas)
        case UniteRecurrence.SEMAINE:
            return ancre + dt.timedelta(weeks=pas)
        case UniteRecurrence.MOIS:
            return _decaler_mois(ancre, pas)
        case UniteRecurrence.AN:
            return _decaler_mois(ancre, pas * 12)


def echeances(
    ancre: dt.date,
    cadence: Cadence,
    *,
    jusqu_a: dt.date,
    depuis: dt.date | None = None,
    fin: dt.date | None = None,
) -> Iterator[dt.date]:
    """Échéances comprises dans `[depuis, jusqu_a]`, bornes incluses.

    `fin` est la date de fin de la récurrence elle-même (résiliation d'un abonnement) :
    aucune échéance n'est produite au-delà.

    La génération part du rang 0 et avance ; elle ne saute pas directement au premier rang
    utile. C'est volontairement naïf : pour un budget de foyer, les fenêtres se comptent en
    mois, et un calcul astucieux serait une source de décalage d'un rang pour un gain nul.
    """
    borne_haute = min(jusqu_a, fin) if fin is not None else jusqu_a
    rang = 0
    while True:
        jour = echeance(ancre, cadence, rang)
        if jour > borne_haute:
            return
        if depuis is None or jour >= depuis:
            yield jour
        rang += 1
        if rang > 10_000:  # garde-fou : une cadence absurde ne doit pas boucler sans fin
            raise RuntimeError("Trop d'échéances : la cadence est probablement erronée.")


def prochaine_echeance(
    ancre: dt.date, cadence: Cadence, *, a_partir_de: dt.date, fin: dt.date | None = None
) -> dt.date | None:
    """Première échéance à `a_partir_de` ou après, ou None si la récurrence est terminée."""
    horizon = a_partir_de + dt.timedelta(days=400)
    for jour in echeances(ancre, cadence, depuis=a_partir_de, jusqu_a=horizon, fin=fin):
        return jour
    return None
