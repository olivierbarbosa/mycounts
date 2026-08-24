"""Machine d'états des cycles réels, sans redécoupage depuis l'historique."""

from __future__ import annotations

import datetime as dt
from uuid import UUID

import pytest
from mycounts.domain.cycles import (
    CycleBudgetaire,
    CycleInvalide,
    EtatCycle,
    ouvrir_correction,
    ouvrir_cycle,
    valider_rattachement,
)

J = dt.date
ESPACE = UUID(int=1)
CYCLE_1 = UUID(int=11)
CYCLE_2 = UUID(int=12)
PAIE_1 = UUID(int=21)
PAIE_2 = UUID(int=22)
AUTEUR = UUID(int=31)


def _cycle_ouvert() -> CycleBudgetaire:
    return CycleBudgetaire(
        identifiant=CYCLE_1,
        espace_id=ESPACE,
        operation_ouverture_id=PAIE_1,
        debut=J(2026, 7, 28),
    )


def _cycle_clos() -> CycleBudgetaire:
    transition = ouvrir_cycle(
        identifiant=CYCLE_2,
        espace_id=ESPACE,
        operation_ouverture_id=PAIE_2,
        date_paie=J(2026, 8, 27),
        cycle_ouvert=_cycle_ouvert(),
    )
    assert transition.cycle_precedent is not None
    return transition.cycle_precedent


def test_la_premiere_paie_ouvre_un_cycle_sans_cloture() -> None:
    transition = ouvrir_cycle(
        identifiant=CYCLE_1,
        espace_id=ESPACE,
        operation_ouverture_id=PAIE_1,
        date_paie=J(2026, 7, 28),
        cycle_ouvert=None,
    )
    assert transition.cycle_precedent is None
    assert transition.nouveau_cycle == _cycle_ouvert()


def test_la_paie_suivante_ferme_et_ouvre_atomiquement() -> None:
    transition = ouvrir_cycle(
        identifiant=CYCLE_2,
        espace_id=ESPACE,
        operation_ouverture_id=PAIE_2,
        date_paie=J(2026, 8, 27),
        cycle_ouvert=_cycle_ouvert(),
    )
    ferme = transition.cycle_precedent
    assert ferme is not None
    assert ferme.etat is EtatCycle.CLOS
    assert ferme.fin_exclusive == J(2026, 8, 27)
    assert ferme.operation_cloture_id == PAIE_2
    assert transition.nouveau_cycle.debut == J(2026, 8, 27)
    assert transition.nouveau_cycle.etat is EtatCycle.OUVERT


def test_les_intervalles_ne_se_chevauchent_pas_sur_la_paie() -> None:
    transition = ouvrir_cycle(
        identifiant=CYCLE_2,
        espace_id=ESPACE,
        operation_ouverture_id=PAIE_2,
        date_paie=J(2026, 8, 27),
        cycle_ouvert=_cycle_ouvert(),
    )
    assert transition.cycle_precedent is not None
    assert not transition.cycle_precedent.contient(J(2026, 8, 27))
    assert transition.nouveau_cycle.contient(J(2026, 8, 27))


@pytest.mark.parametrize(
    ("date_paie", "motif"),
    [(J(2026, 7, 28), "postérieure"), (J(2026, 7, 1), "postérieure")],
)
def test_un_cycle_nul_ou_inverse_est_refuse(date_paie: dt.date, motif: str) -> None:
    with pytest.raises(CycleInvalide, match=motif):
        ouvrir_cycle(
            identifiant=CYCLE_2,
            espace_id=ESPACE,
            operation_ouverture_id=PAIE_2,
            date_paie=date_paie,
            cycle_ouvert=_cycle_ouvert(),
        )


def test_deux_espaces_ne_peuvent_pas_partager_la_transition() -> None:
    with pytest.raises(CycleInvalide, match="espaces"):
        ouvrir_cycle(
            identifiant=CYCLE_2,
            espace_id=UUID(int=999),
            operation_ouverture_id=PAIE_2,
            date_paie=J(2026, 8, 27),
            cycle_ouvert=_cycle_ouvert(),
        )


def test_un_etat_persisted_incomplet_est_refuse() -> None:
    with pytest.raises(CycleInvalide, match="exige"):
        CycleBudgetaire(
            identifiant=CYCLE_1,
            espace_id=ESPACE,
            operation_ouverture_id=PAIE_1,
            debut=J(2026, 7, 28),
            etat=EtatCycle.CLOS,
        )


def test_corriger_un_cycle_clos_incremente_la_version_sans_bouger_les_bornes() -> None:
    avant = _cycle_clos()
    maintenant = dt.datetime(2026, 8, 30, 10, 0, tzinfo=dt.UTC)
    resultat = ouvrir_correction(
        avant,
        auteur_id=AUTEUR,
        motif="  opération oubliée  ",
        cree_le=maintenant,
    )
    assert resultat.cycle.debut == avant.debut
    assert resultat.cycle.fin_exclusive == avant.fin_exclusive
    assert resultat.cycle.version_correction == 1
    assert resultat.evenement.ancienne_version == 0
    assert resultat.evenement.nouvelle_version == 1
    assert resultat.evenement.motif == "opération oubliée"


def test_correction_refusee_sur_cycle_ouvert_ou_sans_motif() -> None:
    with pytest.raises(CycleInvalide, match="cycle ouvert"):
        ouvrir_correction(
            _cycle_ouvert(), auteur_id=AUTEUR, motif="raison", cree_le=dt.datetime.now(dt.UTC)
        )
    with pytest.raises(CycleInvalide, match="expliquée"):
        ouvrir_correction(
            _cycle_clos(), auteur_id=AUTEUR, motif="  ", cree_le=dt.datetime.now(dt.UTC)
        )


def test_une_operation_ordinaire_ne_modifie_pas_un_cycle_clos() -> None:
    cycle = _cycle_clos()
    with pytest.raises(CycleInvalide, match="correction ouverte"):
        valider_rattachement(cycle, espace_id=ESPACE, date_operation=J(2026, 8, 12))
    correction = ouvrir_correction(
        cycle,
        auteur_id=AUTEUR,
        motif="opération oubliée",
        cree_le=dt.datetime.now(dt.UTC),
    )
    valider_rattachement(
        correction.cycle,
        espace_id=ESPACE,
        date_operation=J(2026, 8, 12),
        version_correction=correction.cycle.version_correction,
    )


def test_rattachement_refuse_hors_bornes_et_hors_espace() -> None:
    cycle = _cycle_ouvert()
    with pytest.raises(CycleInvalide, match="hors des bornes"):
        valider_rattachement(cycle, espace_id=ESPACE, date_operation=J(2026, 7, 27))
    with pytest.raises(CycleInvalide, match="même espace"):
        valider_rattachement(cycle, espace_id=UUID(int=404), date_operation=J(2026, 7, 28))
