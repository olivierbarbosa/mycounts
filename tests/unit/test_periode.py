"""Tests de la période budgétaire.

Le contrôle central est `test_temoin_la_date_de_saisie_ne_fuit_pas` : il compare deux
scénarios qui doivent donner exactement les mêmes bornes, et échouerait si la date de
saisie entrait dans le calcul.
"""

from __future__ import annotations

import datetime as dt

import pytest
from mycounts.domain.periode import (
    Periode,
    ajouter_un_mois,
    dates_ouvrantes,
    periode_contenant,
    periode_courante,
    periodes,
)

J = dt.date


# --- Ajout d'un mois : le piège des fins de mois ----------------------------------


@pytest.mark.parametrize(
    ("depart", "attendu"),
    [
        (J(2026, 1, 15), J(2026, 2, 15)),
        (J(2026, 1, 31), J(2026, 2, 28)),  # février n'a pas de 31
        (J(2028, 1, 31), J(2028, 2, 29)),  # bissextile
        (J(2026, 1, 30), J(2026, 2, 28)),
        (J(2026, 3, 31), J(2026, 4, 30)),
        (J(2026, 12, 31), J(2027, 1, 31)),  # passage d'année
        (J(2026, 12, 15), J(2027, 1, 15)),
    ],
)
def test_ajouter_un_mois(depart: dt.date, attendu: dt.date) -> None:
    """Sans le rabattement au dernier jour, une paie du 31 produirait une période d'un
    seul jour tous les deux mois."""
    assert ajouter_un_mois(depart) == attendu


def test_ajouter_un_mois_ne_deborde_jamais_sur_le_mois_suivant() -> None:
    """Témoin : `jour + 31 jours` donnerait le 3 mars depuis le 31 janvier."""
    for mois in range(1, 13):
        for jour in (28, 29, 30, 31):
            try:
                depart = J(2026, mois, jour)
            except ValueError:
                continue
            resultat = ajouter_un_mois(depart)
            attendu_mois = depart.month % 12 + 1
            assert resultat.month == attendu_mois, f"{depart} a débordé sur {resultat}"


# --- Découpage en périodes -------------------------------------------------------


def test_deux_paies_donnent_une_periode_close_et_une_estimee() -> None:
    resultat = periodes([J(2026, 6, 27), J(2026, 7, 28)], aujourd_hui=J(2026, 8, 10))
    assert resultat == [
        Periode(debut=J(2026, 6, 27), fin=J(2026, 7, 27), fin_estimee=False),
        Periode(debut=J(2026, 7, 28), fin=J(2026, 8, 27), fin_estimee=True),
    ]


def test_les_bornes_sont_jointives_sans_trou_ni_chevauchement() -> None:
    """Témoin structurel : chaque jour appartient à exactement une période.

    Un trou d'un jour ferait disparaître les opérations de ce jour de tous les totaux —
    exactement la classe d'erreur d'ERREURS.md #010.
    """
    paies = [J(2026, 1, 31), J(2026, 2, 27), J(2026, 3, 31), J(2026, 4, 30)]
    resultat = periodes(paies, aujourd_hui=J(2026, 5, 10))
    for precedente, suivante in zip(resultat, resultat[1:], strict=False):
        assert precedente.fin + dt.timedelta(days=1) == suivante.debut, (
            f"trou ou chevauchement entre {precedente} et {suivante}"
        )


def test_sans_aucune_paie_on_retombe_sur_le_mois_civil_marque_estime() -> None:
    resultat = periodes([], aujourd_hui=J(2026, 8, 19))
    assert resultat == [Periode(debut=J(2026, 8, 1), fin=J(2026, 8, 31), fin_estimee=True)]


def test_les_paies_desordonnees_sont_triees() -> None:
    desordre = periodes([J(2026, 7, 28), J(2026, 6, 27)], aujourd_hui=J(2026, 8, 10))
    ordre = periodes([J(2026, 6, 27), J(2026, 7, 28)], aujourd_hui=J(2026, 8, 10))
    assert desordre == ordre


# --- Le témoin central -----------------------------------------------------------


def test_temoin_la_date_de_saisie_ne_fuit_pas() -> None:
    """Une paie du 27 saisie le 30 doit donner EXACTEMENT les mêmes bornes qu'une paie
    du 27 saisie le 27.

    C'est la mesure qui peut rendre la réponse inverse : si la date de saisie entrait
    dans le calcul, les deux appels différeraient. Le seul paramètre qui varie ici est
    « aujourd'hui », c'est-à-dire le jour où l'on regarde.
    """
    paies = [J(2026, 8, 27)]
    ponctuel = periode_courante(paies, aujourd_hui=J(2026, 8, 27))
    en_retard = periode_courante(paies, aujourd_hui=J(2026, 8, 30))
    assert ponctuel == en_retard
    assert ponctuel.debut == J(2026, 8, 27)


def test_temoin_les_periodes_ne_sont_pas_toutes_identiques() -> None:
    """Contrôle inverse : sur des paies différentes, les périodes diffèrent.

    Sans lui, une implémentation renvoyant toujours la même période passerait le témoin
    ci-dessus sans effort.
    """
    a = periode_courante([J(2026, 8, 5)], aujourd_hui=J(2026, 8, 19))
    b = periode_courante([J(2026, 8, 15)], aujourd_hui=J(2026, 8, 19))
    assert a != b
    assert a.debut != b.debut


# --- Plusieurs paies par cycle ---------------------------------------------------


def test_une_paie_sur_deux_ouvre_le_cycle() -> None:
    """Payé deux fois par mois : la seconde paie est un revenu dans la période, elle ne
    rouvre rien. Sinon les plafonds repartiraient à zéro en plein mois."""
    paies = [J(2026, 6, 15), J(2026, 6, 30), J(2026, 7, 15), J(2026, 7, 31)]
    assert dates_ouvrantes(paies, paies_par_cycle=2) == [J(2026, 6, 15), J(2026, 7, 15)]

    resultat = periodes(paies, aujourd_hui=J(2026, 7, 20), paies_par_cycle=2)
    assert len(resultat) == 2
    assert resultat[0] == Periode(debut=J(2026, 6, 15), fin=J(2026, 7, 14), fin_estimee=False)


def test_paies_par_cycle_invalide_refuse() -> None:
    with pytest.raises(ValueError, match="au moins une paie"):
        dates_ouvrantes([J(2026, 6, 15)], paies_par_cycle=0)


# --- Jours hors des périodes observées -------------------------------------------


def test_un_jour_anterieur_a_la_premiere_paie_a_sa_propre_periode() -> None:
    """Le compter dans la première période l'inclurait dans un budget qui n'avait pas
    encore commencé."""
    resultat = periode_contenant(
        J(2026, 6, 10), [J(2026, 6, 27)], aujourd_hui=J(2026, 7, 1)
    )
    assert resultat.fin == J(2026, 6, 26)
    assert not resultat.contient(J(2026, 6, 27))


def test_une_echeance_lointaine_recoit_une_periode_prolongee() -> None:
    """Une échéance à six mois doit avoir une période d'accueil, pas une erreur."""
    resultat = periode_contenant(
        J(2027, 2, 3), [J(2026, 8, 27)], aujourd_hui=J(2026, 8, 27)
    )
    assert resultat.contient(J(2027, 2, 3))
    assert resultat.fin_estimee


def test_chaque_jour_dune_annee_recoit_exactement_une_periode() -> None:
    """Témoin de couverture : aucun jour ne doit être orphelin.

    Parcourt une année entière autour des paies connues et vérifie qu'une période
    contenant le jour est toujours renvoyée.
    """
    paies = [J(2026, 6, 27), J(2026, 7, 28), J(2026, 8, 27)]
    jour = J(2026, 1, 1)
    while jour < J(2027, 6, 1):
        resultat = periode_contenant(jour, paies, aujourd_hui=J(2026, 8, 30))
        assert resultat.contient(jour), f"{jour} n'appartient à aucune période"
        jour += dt.timedelta(days=1)
