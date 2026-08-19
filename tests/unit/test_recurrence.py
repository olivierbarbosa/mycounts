"""Tests des échéances récurrentes.

Le test central est `test_temoin_le_31_revient_apres_fevrier` : c'est la mesure qui
distingue un calcul partant de l'ancre d'un calcul partant de l'échéance précédente. La
seconde implémentation semble juste pendant deux mois, puis dérive définitivement.
"""

from __future__ import annotations

import datetime as dt

import pytest
from mycounts.domain.recurrence import (
    Cadence,
    UniteRecurrence,
    echeance,
    echeances,
    prochaine_echeance,
)

J = dt.date
MENSUEL = Cadence(UniteRecurrence.MOIS)


def liste(ancre: dt.date, cadence: Cadence, jusqu_a: dt.date, **kw: object) -> list[dt.date]:
    return list(echeances(ancre, cadence, jusqu_a=jusqu_a, **kw))  # type: ignore[arg-type]


# --- Le témoin central -----------------------------------------------------------


def test_temoin_le_31_revient_apres_fevrier() -> None:
    """Une récurrence au 31 glisse au 28 en février PUIS revient au 31 en mars.

    Un calcul qui partirait de l'échéance précédente resterait bloqué au 28 pour
    toujours : le prélèvement réel, lui, retomberait au 31, et l'écart ne se verrait
    qu'après plusieurs mois d'agenda faux.
    """
    obtenu = liste(J(2026, 1, 31), MENSUEL, J(2026, 6, 30))
    assert obtenu == [
        J(2026, 1, 31),
        J(2026, 2, 28),
        J(2026, 3, 31),  # le quantième d'origine est retrouvé
        J(2026, 4, 30),
        J(2026, 5, 31),
        J(2026, 6, 30),
    ]


def test_temoin_les_echeances_ne_sont_pas_toutes_le_meme_jour() -> None:
    """Contrôle inverse : sur un quantième qui existe partout, aucune dérive non plus.

    Sans ce volet, une implémentation qui renverrait toujours le même jour du mois
    passerait le témoin ci-dessus par accident.
    """
    obtenu = liste(J(2026, 1, 15), MENSUEL, J(2026, 4, 30))
    assert obtenu == [J(2026, 1, 15), J(2026, 2, 15), J(2026, 3, 15), J(2026, 4, 15)]
    assert len({jour.month for jour in obtenu}) == 4


def test_le_29_fevrier_bissextile_est_retrouve_tous_les_quatre_ans() -> None:
    obtenu = [echeance(J(2028, 2, 29), Cadence(UniteRecurrence.AN), rang) for rang in range(5)]
    assert obtenu == [
        J(2028, 2, 29),
        J(2029, 2, 28),
        J(2030, 2, 28),
        J(2031, 2, 28),
        J(2032, 2, 29),  # de nouveau bissextile
    ]


# --- Cadences --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cadence", "attendu"),
    [
        (Cadence(UniteRecurrence.JOUR), [J(2026, 8, 1), J(2026, 8, 2), J(2026, 8, 3)]),
        (Cadence(UniteRecurrence.JOUR, 10), [J(2026, 8, 1), J(2026, 8, 11), J(2026, 8, 21)]),
        (Cadence(UniteRecurrence.SEMAINE), [J(2026, 8, 1), J(2026, 8, 8), J(2026, 8, 15)]),
        (Cadence(UniteRecurrence.SEMAINE, 2), [J(2026, 8, 1), J(2026, 8, 15), J(2026, 8, 29)]),
        (Cadence(UniteRecurrence.MOIS, 3), [J(2026, 8, 1), J(2026, 11, 1), J(2027, 2, 1)]),
    ],
)
def test_cadences(cadence: Cadence, attendu: list[dt.date]) -> None:
    assert [echeance(J(2026, 8, 1), cadence, rang) for rang in range(3)] == attendu


def test_un_intervalle_nul_est_refuse() -> None:
    with pytest.raises(ValueError, match="au moins 1"):
        Cadence(UniteRecurrence.MOIS, 0)


def test_un_rang_negatif_est_refuse() -> None:
    with pytest.raises(ValueError, match="négatif"):
        echeance(J(2026, 8, 1), MENSUEL, -1)


# --- Fenêtres et fin de récurrence -----------------------------------------------


def test_la_fenetre_est_inclusive_des_deux_cotes() -> None:
    assert liste(J(2026, 8, 1), MENSUEL, J(2026, 10, 1)) == [
        J(2026, 8, 1),
        J(2026, 9, 1),
        J(2026, 10, 1),
    ]


def test_une_recurrence_terminee_ne_produit_plus_rien() -> None:
    """Un abonnement résilié ne doit pas continuer à peupler l'agenda."""
    obtenu = liste(J(2026, 8, 1), MENSUEL, J(2026, 12, 1), fin=J(2026, 9, 15))
    assert obtenu == [J(2026, 8, 1), J(2026, 9, 1)]


def test_le_filtre_depuis_ne_decale_pas_les_dates() -> None:
    """Filtrer une fenêtre ne doit pas changer le calendrier : les dates restent
    calculées depuis l'ancre, seul l'affichage est restreint."""
    completes = liste(J(2026, 1, 31), MENSUEL, J(2026, 6, 30))
    filtrees = liste(J(2026, 1, 31), MENSUEL, J(2026, 6, 30), depuis=J(2026, 3, 1))
    assert filtrees == [jour for jour in completes if jour >= J(2026, 3, 1)]
    assert J(2026, 3, 31) in filtrees


def test_prochaine_echeance() -> None:
    assert prochaine_echeance(J(2026, 1, 31), MENSUEL, a_partir_de=J(2026, 3, 1)) == J(2026, 3, 31)


def test_prochaine_echeance_dune_recurrence_terminee_est_nulle() -> None:
    assert (
        prochaine_echeance(
            J(2026, 1, 1), MENSUEL, a_partir_de=J(2026, 6, 1), fin=J(2026, 3, 1)
        )
        is None
    )


def test_une_cadence_absurde_ne_boucle_pas_sans_fin() -> None:
    """Garde-fou : une génération quotidienne sur un siècle doit s'arrêter net plutôt
    que de remplir la mémoire."""
    with pytest.raises(RuntimeError, match="Trop d'échéances"):
        liste(J(2026, 1, 1), Cadence(UniteRecurrence.JOUR), J(2126, 1, 1))
