"""Du contexte métier à une proposition mensuelle exacte et explicable."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from itertools import permutations
from uuid import UUID

import pytest
from mycounts.domain.montants import Cents
from mycounts.domain.recommandation_enveloppes import (
    EnveloppePourRecommandation,
    OrigineRythme,
    RecommandationInvalide,
    TypeEnveloppe,
    calculer_souhaits_mensuels,
    recommander_repartition_mensuelle,
)

J = dt.date
A = UUID(int=1)
B = UUID(int=2)
C = UUID(int=3)
DATE_CIBLE = J(2026, 12, 24)


def _objectif(
    identifiant: UUID,
    *,
    solde: int = 0,
    cible: int = 120_000,
    date_cible: dt.date = DATE_CIBLE,
    importance: int = 3,
    contribution: int | None = None,
) -> EnveloppePourRecommandation:
    return EnveloppePourRecommandation(
        enveloppe_id=identifiant,
        type=TypeEnveloppe.OBJECTIF,
        solde=Cents(solde),
        importance=importance,
        cible=Cents(cible),
        date_cible=date_cible,
        contribution_mensuelle=None if contribution is None else Cents(contribution),
    )


def _prevention(
    identifiant: UUID,
    *,
    solde: int = 0,
    cible: int | None = 100_000,
    importance: int = 3,
    contribution: int | None = None,
) -> EnveloppePourRecommandation:
    return EnveloppePourRecommandation(
        enveloppe_id=identifiant,
        type=TypeEnveloppe.PREVENTION,
        solde=Cents(solde),
        importance=importance,
        cible=None if cible is None else Cents(cible),
        contribution_mensuelle=None if contribution is None else Cents(contribution),
    )


def test_un_objectif_date_divise_exactement_le_manque_sur_les_mois_restants() -> None:
    [souhait] = calculer_souhaits_mensuels(
        (_objectif(A, cible=100_001, date_cible=J(2026, 11, 24)),),
        aujourd_hui=J(2026, 8, 24),
    )
    assert souhait.origine is OrigineRythme.ECHEANCE
    assert souhait.rythme == Cents(33_334), "100001 / 3, arrondi au centime supérieur"
    assert souhait.manque == Cents(100_001)


@pytest.mark.parametrize("date_cible", [J(2020, 1, 1), J(2026, 8, 1), J(2026, 8, 31)])
def test_une_echeance_passee_ou_dans_le_mois_demande_le_reste_maintenant(
    date_cible: dt.date,
) -> None:
    [souhait] = calculer_souhaits_mensuels(
        (_objectif(A, cible=40_000, solde=10_000, date_cible=date_cible),),
        aujourd_hui=J(2026, 8, 24),
    )
    assert souhait.rythme == Cents(30_000)


def test_la_contribution_ecrite_prime_sur_la_date_deduite() -> None:
    [souhait] = calculer_souhaits_mensuels(
        (_objectif(A, cible=100_000, date_cible=J(2026, 9, 24), contribution=12_345),),
        aujourd_hui=J(2026, 8, 24),
    )
    assert souhait.origine is OrigineRythme.CONTRIBUTION
    assert souhait.rythme == Cents(12_345)


def test_une_enveloppe_suffisamment_couverte_recoit_toujours_zero() -> None:
    proposition = recommander_repartition_mensuelle(
        Cents(50_000),
        (_prevention(A, solde=120_000, cible=100_000, importance=5),),
        aujourd_hui=J(2026, 8, 24),
    )
    assert proposition.lignes[0].origine is OrigineRythme.COUVERTE
    assert proposition.lignes[0].poids == 0
    assert proposition.lignes[0].montant == Cents(0)
    assert proposition.montant_non_affecte == Cents(50_000)


def test_une_prevention_sans_niveau_valide_reste_a_configurer_et_recoit_zero() -> None:
    proposition = recommander_repartition_mensuelle(
        Cents(10_000),
        (_prevention(A, cible=None),),
        aujourd_hui=J(2026, 8, 24),
    )
    assert proposition.lignes[0].origine is OrigineRythme.A_CONFIGURER
    assert proposition.lignes[0].montant == Cents(0)


def test_a_besoin_egal_limportance_forte_recoit_davantage() -> None:
    proposition = recommander_repartition_mensuelle(
        Cents(50_000),
        (
            _prevention(A, cible=100_000, importance=1),
            _prevention(B, cible=100_000, importance=5),
        ),
        aujourd_hui=J(2026, 8, 24),
    )
    montants = {ligne.enveloppe_id: ligne.montant for ligne in proposition.lignes}
    assert montants[B] > montants[A]
    assert sum(int(montant) for montant in montants.values()) == 50_000


def test_a_egalite_parfaite_le_centime_va_a_luuid_stable() -> None:
    proposition = recommander_repartition_mensuelle(
        Cents(101),
        (_prevention(B), _prevention(A)),
        aujourd_hui=J(2026, 8, 24),
    )
    montants = {ligne.enveloppe_id: ligne.montant for ligne in proposition.lignes}
    assert montants == {A: Cents(51), B: Cents(50)}


def test_un_objectif_plus_proche_pese_plus_que_le_meme_objectif_lointain() -> None:
    [proche, loin] = calculer_souhaits_mensuels(
        (
            _objectif(A, date_cible=J(2026, 9, 24), importance=3),
            _objectif(B, date_cible=J(2027, 8, 24), importance=3),
        ),
        aujourd_hui=J(2026, 8, 24),
    )
    assert proche.poids > loin.poids


def test_le_rythme_et_le_manque_bornent_la_proposition() -> None:
    proposition = recommander_repartition_mensuelle(
        Cents(100_000),
        (
            _objectif(A, solde=99_000, cible=100_000, contribution=50_000),
            _prevention(B, solde=0, cible=100_000, contribution=2_000),
        ),
        aujourd_hui=J(2026, 8, 24),
    )
    montants = {ligne.enveloppe_id: ligne.montant for ligne in proposition.lignes}
    assert montants == {A: Cents(1_000), B: Cents(2_000)}
    assert proposition.montant_non_affecte == Cents(97_000)


def test_chaque_centime_choisi_est_affecte_ou_explique_comme_non_affecte() -> None:
    enveloppes = (
        _objectif(A, solde=20_000, cible=123_457, date_cible=J(2026, 11, 24)),
        _prevention(B, solde=10_000, cible=80_000, contribution=12_345, importance=5),
        _prevention(C, solde=50_000, cible=50_000),
    )
    for montant in range(2_001):
        proposition = recommander_repartition_mensuelle(
            Cents(montant), enveloppes, aujourd_hui=J(2026, 8, 24)
        )
        assert proposition.total_explique == Cents(montant)
        assert proposition.montant_affecte == Cents(
            sum(int(ligne.montant) for ligne in proposition.lignes)
        )
        assert all(Cents(0) <= ligne.montant <= ligne.rythme for ligne in proposition.lignes)


def test_lordre_dentree_ne_change_pas_la_proposition() -> None:
    enveloppes = (
        _objectif(A, importance=5),
        _prevention(B, importance=2, contribution=23_000),
        _prevention(C, importance=2, contribution=23_000),
    )
    propositions = {
        recommander_repartition_mensuelle(Cents(50_003), tuple(ordre), aujourd_hui=J(2026, 8, 24))
        for ordre in permutations(enveloppes)
    }
    assert len(propositions) == 1


CONFIGURATIONS_INVALIDES: tuple[Callable[[], object], ...] = (
    lambda: _prevention(A, importance=0),
    lambda: _prevention(A, importance=6),
    lambda: _objectif(A, cible=0),
    lambda: EnveloppePourRecommandation(A, TypeEnveloppe.OBJECTIF, Cents(0), 3),
    lambda: EnveloppePourRecommandation(
        A,
        TypeEnveloppe.PREVENTION,
        Cents(0),
        3,
        cible=Cents(100),
        date_cible=J(2026, 9, 1),
    ),
)


@pytest.mark.parametrize("fabrique", CONFIGURATIONS_INVALIDES)
def test_les_configurations_incoherentes_sont_refusees(
    fabrique: Callable[[], object],
) -> None:
    with pytest.raises(RecommandationInvalide):
        fabrique()


def test_les_doublons_sont_refuses() -> None:
    with pytest.raises(RecommandationInvalide, match="qu'une fois"):
        calculer_souhaits_mensuels((_prevention(A), _objectif(A)), aujourd_hui=J(2026, 8, 24))
