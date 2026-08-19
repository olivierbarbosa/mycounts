"""Tests du calendrier.

`test_minuit_le_dernier_jour_du_mois` est le contrôle qui peut rendre la réponse
inverse : une implémentation qui ignore le fuseau y répond 31 janvier au lieu du
1er février.
"""

from __future__ import annotations

import datetime as dt

import pytest
from mycounts.domain.calendrier import aujourd_hui, bornes_du_mois


@pytest.mark.parametrize(
    ("jour", "debut", "fin"),
    [
        (dt.date(2026, 8, 19), dt.date(2026, 8, 1), dt.date(2026, 8, 31)),
        (dt.date(2026, 12, 5), dt.date(2026, 12, 1), dt.date(2026, 12, 31)),
        (dt.date(2026, 1, 1), dt.date(2026, 1, 1), dt.date(2026, 1, 31)),
        (dt.date(2028, 2, 10), dt.date(2028, 2, 1), dt.date(2028, 2, 29)),  # bissextile
        (dt.date(2026, 2, 10), dt.date(2026, 2, 1), dt.date(2026, 2, 28)),
    ],
)
def test_bornes_du_mois(jour: dt.date, debut: dt.date, fin: dt.date) -> None:
    assert bornes_du_mois(jour) == (debut, fin)


def test_minuit_le_dernier_jour_du_mois() -> None:
    """31/01 23h30 UTC est déjà le 1er février à Paris.

    Le choix est écrit ici : la date civile du foyer fait foi. Une opération saisie à ce
    moment-là appartient à février, et un rapprochement de fin de mois qui compterait
    janvier serait faux d'une opération.
    """
    instant = dt.datetime(2026, 1, 31, 23, 30, tzinfo=dt.UTC)
    assert instant.date() == dt.date(2026, 1, 31)  # en UTC
    assert aujourd_hui(instant) == dt.date(2026, 2, 1)  # à Paris


def test_changement_dheure_ne_decale_pas_la_date() -> None:
    """Le dimanche du passage à l'heure d'été 2026 (29 mars) reste un seul jour civil."""
    matin = dt.datetime(2026, 3, 29, 0, 30, tzinfo=dt.UTC)
    soir = dt.datetime(2026, 3, 29, 21, 30, tzinfo=dt.UTC)
    assert aujourd_hui(matin) == dt.date(2026, 3, 29)
    assert aujourd_hui(soir) == dt.date(2026, 3, 29)


def test_instant_sans_fuseau_refuse() -> None:
    with pytest.raises(ValueError, match="sans fuseau"):
        aujourd_hui(dt.datetime(2026, 8, 19, 12, 0))  # noqa: DTZ001 — c'est le cas testé
