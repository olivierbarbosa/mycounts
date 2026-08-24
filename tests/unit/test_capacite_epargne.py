"""Capacités d'épargne : l'ordre des trois scénarios est un invariant monétaire."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import replace

import pytest
from mycounts.domain.capacite_epargne import (
    VERSION_CALCUL,
    CapaciteInvalide,
    ConfianceCapacite,
    EntreesCapaciteEpargne,
    calculer_capacites,
)
from mycounts.domain.montants import Cents

J = dt.date


def _entrees() -> EntreesCapaciteEpargne:
    return EntreesCapaciteEpargne(
        solde_actuel=Cents(250_000),
        date_du_solde=J(2026, 8, 27),
        prochaine_paie_estimee=J(2026, 9, 27),
        revenus_avant_paie=Cents(20_000),
        charges_recurrentes_avant_paie=Cents(80_000),
        budget_variable_restant=Cents(70_000),
        train_de_vie_habituel_restant=Cents(50_000),
        depenses_exceptionnelles_confirmees=Cents(10_000),
        solde_de_securite=Cents(30_000),
        marge_de_prudence=Cents(15_000),
        epargne_existante=Cents(2_000_000),
        cycles_clos_observes=2,
    )


def test_formule_v1_est_explicable_centime_par_centime() -> None:
    resultat = calculer_capacites(_entrees())
    # Socle = 2500 + 200 - 800 - 100 - 300 = 1500 €.
    # Recommandé conserve le budget haut (700), ambitieux l'habitude basse (500),
    # prudent ajoute la marge de 150.
    assert resultat.prudente == Cents(65_000)
    assert resultat.recommandee == Cents(80_000)
    assert resultat.ambitieuse == Cents(100_000)
    assert resultat.version_calcul == VERSION_CALCUL


def test_les_capacites_sont_bornees_a_zero_et_ordonnees() -> None:
    resultat = calculer_capacites(
        replace(_entrees(), solde_actuel=Cents(-100_000), revenus_avant_paie=Cents(0))
    )
    assert resultat.prudente == resultat.recommandee == resultat.ambitieuse == Cents(0)


def test_une_source_de_train_de_vie_absente_nest_pas_interpretee_comme_zero_depense() -> None:
    sans_budget = calculer_capacites(replace(_entrees(), budget_variable_restant=Cents(0)))
    sans_historique = calculer_capacites(
        replace(_entrees(), train_de_vie_habituel_restant=Cents(0))
    )
    assert sans_budget.recommandee == sans_budget.ambitieuse
    assert sans_historique.recommandee == sans_historique.ambitieuse


def test_le_stock_depargne_existant_ne_gonfle_jamais_la_capacite_du_quotidien() -> None:
    sans_epargne = calculer_capacites(replace(_entrees(), epargne_existante=Cents(0)))
    vingt_millions = calculer_capacites(replace(_entrees(), epargne_existante=Cents(2_000_000_000)))
    assert sans_epargne == vingt_millions


@pytest.mark.parametrize(
    ("cycles", "confiance"),
    [
        (0, ConfianceCapacite.FAIBLE),
        (2, ConfianceCapacite.FAIBLE),
        (3, ConfianceCapacite.MOYENNE),
        (5, ConfianceCapacite.MOYENNE),
        (6, ConfianceCapacite.HAUTE),
        (24, ConfianceCapacite.HAUTE),
    ],
)
def test_lhistorique_change_la_confiance_pas_les_montants(
    cycles: int, confiance: ConfianceCapacite
) -> None:
    reference = calculer_capacites(_entrees())
    resultat = calculer_capacites(replace(_entrees(), cycles_clos_observes=cycles))
    assert resultat.confiance is confiance
    assert (resultat.prudente, resultat.recommandee, resultat.ambitieuse) == (
        reference.prudente,
        reference.recommandee,
        reference.ambitieuse,
    )


MODIFICATIONS_INVALIDES: tuple[Callable[[EntreesCapaciteEpargne], EntreesCapaciteEpargne], ...] = (
    lambda e: replace(e, revenus_avant_paie=Cents(-1)),
    lambda e: replace(e, charges_recurrentes_avant_paie=Cents(-1)),
    lambda e: replace(e, budget_variable_restant=Cents(-1)),
    lambda e: replace(e, train_de_vie_habituel_restant=Cents(-1)),
    lambda e: replace(e, depenses_exceptionnelles_confirmees=Cents(-1)),
    lambda e: replace(e, solde_de_securite=Cents(-1)),
    lambda e: replace(e, marge_de_prudence=Cents(-1)),
    lambda e: replace(e, epargne_existante=Cents(-1)),
    lambda e: replace(e, cycles_clos_observes=-1),
    lambda e: replace(e, prochaine_paie_estimee=J(2026, 8, 26)),
)


@pytest.mark.parametrize("modifier", MODIFICATIONS_INVALIDES)
def test_les_entrees_incoherentes_sont_refusees(
    modifier: Callable[[EntreesCapaciteEpargne], EntreesCapaciteEpargne],
) -> None:
    with pytest.raises(CapaciteInvalide):
        modifier(_entrees())


def test_invariant_sur_une_grille_de_scenarios() -> None:
    for solde in (-100_000, 0, 100_000, 1_000_000):
        for budget in (0, 1, 33_333, 500_000):
            for habitudes in (0, 1, 66_667, 600_000):
                resultat = calculer_capacites(
                    replace(
                        _entrees(),
                        solde_actuel=Cents(solde),
                        budget_variable_restant=Cents(budget),
                        train_de_vie_habituel_restant=Cents(habitudes),
                    )
                )
                assert Cents(0) <= resultat.prudente
                assert resultat.prudente <= resultat.recommandee <= resultat.ambitieuse
