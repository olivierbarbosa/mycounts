"""Chaque centime affecté ou repris est exact, ordonné et reproductible."""

from __future__ import annotations

from collections.abc import Callable
from itertools import permutations
from uuid import UUID

import pytest
from mycounts.domain.montants import Cents
from mycounts.domain.repartition_epargne import (
    Affectation,
    EtatEnveloppe,
    RepartitionInvalide,
    SouhaitAffectation,
    planifier_retrait,
    repartir_exactement,
    retablir_couverture,
    valider_affectations_exactes,
)

A = UUID(int=1)
B = UUID(int=2)
C = UUID(int=3)


def _montants(resultat: tuple[Affectation, ...]) -> dict[UUID, Cents]:
    return {ligne.enveloppe_id: ligne.montant for ligne in resultat}


def test_trois_parts_egales_attribuent_le_centime_restant_a_la_priorite() -> None:
    resultat = repartir_exactement(
        Cents(100),
        [
            SouhaitAffectation(A, poids=1, rang_priorite=2),
            SouhaitAffectation(B, poids=1, rang_priorite=0),
            SouhaitAffectation(C, poids=1, rang_priorite=1),
        ],
    )
    assert _montants(resultat) == {A: Cents(33), B: Cents(34), C: Cents(33)}
    assert sum(int(ligne.montant) for ligne in resultat) == 100


def test_un_plafond_redistribue_exactement_son_surplus() -> None:
    resultat = repartir_exactement(
        Cents(100),
        [
            SouhaitAffectation(A, poids=1, maximum=Cents(10)),
            SouhaitAffectation(B, poids=1),
            SouhaitAffectation(C, poids=2),
        ],
    )
    assert _montants(resultat) == {A: Cents(10), B: Cents(30), C: Cents(60)}


def test_lordre_dentree_ne_change_jamais_la_repartition() -> None:
    souhaits = [
        SouhaitAffectation(A, poids=3, rang_priorite=2),
        SouhaitAffectation(B, poids=2, rang_priorite=1),
        SouhaitAffectation(C, poids=1, rang_priorite=0),
    ]
    resultats = {tuple(repartir_exactement(Cents(101), ordre)) for ordre in permutations(souhaits)}
    assert len(resultats) == 1


def test_zero_produit_des_lignes_stables_sans_exiger_de_poids() -> None:
    resultat = repartir_exactement(
        Cents(0), [SouhaitAffectation(B, poids=0), SouhaitAffectation(A, poids=0)]
    )
    assert resultat == (Affectation(A, Cents(0)), Affectation(B, Cents(0)))


def test_aucun_centime_ne_peut_disparaitre_entre_zero_et_deux_cents() -> None:
    souhaits = [
        SouhaitAffectation(A, poids=7, rang_priorite=0),
        SouhaitAffectation(B, poids=11, rang_priorite=1),
        SouhaitAffectation(C, poids=13, rang_priorite=2),
    ]
    for montant in range(2_001):
        resultat = repartir_exactement(Cents(montant), souhaits)
        assert sum(int(ligne.montant) for ligne in resultat) == montant
        assert all(ligne.montant >= 0 for ligne in resultat)


def test_repartition_refuse_absence_de_destinataire_et_capacite_insuffisante() -> None:
    with pytest.raises(RepartitionInvalide, match="Aucune enveloppe"):
        repartir_exactement(Cents(1), [SouhaitAffectation(A, poids=0)])
    with pytest.raises(RepartitionInvalide, match="insuffisante"):
        repartir_exactement(
            Cents(101),
            [
                SouhaitAffectation(A, poids=1, maximum=Cents(50)),
                SouhaitAffectation(B, poids=1, maximum=Cents(50)),
            ],
        )


def test_barriere_valide_uniquement_la_somme_exacte() -> None:
    valider_affectations_exactes(Cents(100), [Affectation(A, Cents(33)), Affectation(B, Cents(67))])
    with pytest.raises(RepartitionInvalide, match="exactement"):
        valider_affectations_exactes(
            Cents(100), [Affectation(A, Cents(33)), Affectation(B, Cents(66))]
        )


def test_retrait_consomme_dabord_le_non_affecte_sans_toucher_aux_enveloppes() -> None:
    plan = planifier_retrait(
        reserve_avant=Cents(100_000),
        retrait=Cents(20_000),
        enveloppes=[EtatEnveloppe(A, Cents(60_000), importance=1)],
    )
    assert plan.non_affecte_consomme == Cents(20_000)
    assert plan.desaffectations == ()
    assert plan.total_explique == plan.retrait


def test_retrait_epuise_le_non_affecte_puis_lenveloppe_la_moins_importante() -> None:
    plan = planifier_retrait(
        reserve_avant=Cents(100_000),
        retrait=Cents(50_000),
        enveloppes=[
            EtatEnveloppe(A, Cents(40_000), importance=1, cible_couverture=Cents(40_000)),
            EtatEnveloppe(B, Cents(40_000), importance=5, cible_couverture=Cents(40_000)),
        ],
    )
    assert plan.non_affecte_consomme == Cents(20_000)
    assert [(ligne.enveloppe_id, ligne.montant) for ligne in plan.desaffectations] == [
        (A, Cents(30_000))
    ]
    assert plan.total_explique == Cents(50_000)


def test_a_importance_egale_la_mieux_couverte_est_reduite_en_premier() -> None:
    resultat = retablir_couverture(
        Cents(100_000),
        [
            EtatEnveloppe(A, Cents(80_000), importance=2, cible_couverture=Cents(40_000)),
            EtatEnveloppe(B, Cents(40_000), importance=2, cible_couverture=Cents(80_000)),
        ],
    )
    assert [(ligne.enveloppe_id, ligne.montant) for ligne in resultat] == [(A, Cents(20_000))]


def test_les_taux_de_couverture_sont_compares_exactement_sans_arrondi() -> None:
    resultat = retablir_couverture(
        Cents(200_000),
        [
            EtatEnveloppe(A, Cents(100_001), importance=2, cible_couverture=Cents(200_000)),
            EtatEnveloppe(B, Cents(100_000), importance=2, cible_couverture=Cents(200_000)),
        ],
    )
    assert resultat == (type(resultat[0])(A, Cents(1)),)


def test_a_egalite_luuid_stable_tranche_independamment_de_lordre_sql() -> None:
    enveloppes = [
        EtatEnveloppe(B, Cents(50), importance=1, cible_couverture=Cents(100)),
        EtatEnveloppe(A, Cents(50), importance=1, cible_couverture=Cents(100)),
    ]
    attendus = {tuple(retablir_couverture(Cents(99), ordre)) for ordre in permutations(enveloppes)}
    assert len(attendus) == 1
    [(ligne,)] = attendus
    assert ligne.enveloppe_id == A
    assert ligne.montant == Cents(1)


def test_correction_de_reserve_retire_exactement_le_surplus_de_couverture() -> None:
    enveloppes = [
        EtatEnveloppe(A, Cents(70_000), importance=1, cible_couverture=Cents(70_000)),
        EtatEnveloppe(B, Cents(60_000), importance=2, cible_couverture=Cents(60_000)),
    ]
    resultat = retablir_couverture(Cents(50_000), enveloppes)
    assert sum(int(ligne.montant) for ligne in resultat) == 80_000
    restants = 130_000 - sum(int(ligne.montant) for ligne in resultat)
    assert restants == 50_000


def test_un_retrait_invalide_ne_masque_pas_un_decouvert_anterieur() -> None:
    with pytest.raises(RepartitionInvalide, match="couverte avant"):
        planifier_retrait(
            reserve_avant=Cents(50),
            retrait=Cents(10),
            enveloppes=[EtatEnveloppe(A, Cents(60), importance=1)],
        )


def test_total_explique_couvre_tout_retrait_sur_une_grille_de_soldes() -> None:
    """Témoin large : non-affecté + reprises explique toujours le retrait complet."""

    for reserve in (0, 1, 7, 31, 100):
        for affecte in range(reserve + 1):
            enveloppes = [
                EtatEnveloppe(
                    A,
                    Cents(affecte // 2),
                    importance=1,
                    cible_couverture=Cents(max(1, affecte)),
                ),
                EtatEnveloppe(
                    B,
                    Cents(affecte - affecte // 2),
                    importance=2,
                    cible_couverture=Cents(max(1, affecte)),
                ),
            ]
            for retrait in range(reserve + 1):
                plan = planifier_retrait(
                    reserve_avant=Cents(reserve),
                    retrait=Cents(retrait),
                    enveloppes=enveloppes,
                )
                repris = sum(int(ligne.montant) for ligne in plan.desaffectations)
                assert plan.total_explique == Cents(retrait)
                assert int(plan.non_affecte_consomme) + repris == retrait
                assert plan.reserve_apres == Cents(reserve - retrait)
                assert affecte - repris <= plan.reserve_apres


@pytest.mark.parametrize(
    "appel",
    [
        lambda: repartir_exactement(Cents(-1), []),
        lambda: repartir_exactement(Cents(1), [SouhaitAffectation(A, 1), SouhaitAffectation(A, 2)]),
        lambda: valider_affectations_exactes(Cents(1), [Affectation(A, Cents(-1))]),
        lambda: retablir_couverture(Cents(-1), []),
        lambda: planifier_retrait(reserve_avant=Cents(10), retrait=Cents(11), enveloppes=[]),
    ],
)
def test_les_invariants_illegaux_sont_refuses(appel: Callable[[], object]) -> None:
    with pytest.raises(RepartitionInvalide):
        appel()
